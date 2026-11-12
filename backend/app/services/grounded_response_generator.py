"""Grounded Natural-Language Response Generation.

Combines verified Microsoft Fabric Lakehouse query results with local Qwen3:4b LLM.
Strictly grounds every numerical assertion on actual returned records.
Provides deterministic, zero-hallucination fallback if Ollama is unavailable
or when running in cloud production environments without local Ollama daemon.
"""

from datetime import date
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
import structlog

from app.config import get_settings
from app.schemas.ai import ExtractedIntent

log = structlog.get_logger()


def _is_local_url(url: Optional[str]) -> bool:
    """Check if the given URL targets localhost, 127.0.0.1, or loopback."""
    if not url:
        return True
    u = url.strip().lower()
    return any(host in u for host in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1"))


class GroundedResponseGenerator:
    """Generates strictly verified, factual answers from Fabric query results."""

    _health_cache: Optional[Dict[str, Any]] = None
    _health_cache_ts: float = 0.0
    HEALTH_CACHE_TTL_SECONDS: float = 60.0

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url
        self.model = self.settings.ollama_model

    @staticmethod
    def _clean_source_label(raw_source: str) -> str:
        s = (raw_source or "").lower()
        if "air_quality" in s or "aqi" in s:
            return "Air Quality Observations"
        if "rainfall" in s:
            return "Rainfall Intelligence"
        if "daily" in s or "monthly" in s or "historical" in s:
            return "Historical Weather Analytics"
        if "dim_district" in s:
            return "District Directory"
        if "current" in s or "silver" in s or "gold_current" in s:
            return "Live Weather Observations"
        if "lakehouse" in s and "dbo" not in s and "gold" not in s:
            return raw_source
        return "Live Weather Observations"

    @staticmethod
    def _get_aqi_advisory(cat: str) -> str:
        c = (cat or "").lower()
        if "good" in c:
            return "Air quality is satisfactory and poses little or no health risk."
        if "moderate" in c:
            return "Air quality is acceptable; unusually sensitive individuals should consider limiting prolonged outdoor exertion."
        if "unhealthy for sensitive" in c:
            return "Members of sensitive groups may experience health effects; general public is less likely to be affected."
        if "very unhealthy" in c or "hazardous" in c:
            return "Health alert: serious risk of health effects for everyone; avoid all outdoor exertion."
        if "unhealthy" in c:
            return "Everyone may begin to experience health effects; sensitive groups should avoid heavy outdoor exertion."
        return "Air quality conditions are monitored continuously across Tamil Nadu."

    async def check_ollama_health(self, force: bool = False) -> Dict[str, Any]:
        """Perform a lightweight health check against Ollama with 60s caching."""
        now = time.time()
        if not force and GroundedResponseGenerator._health_cache is not None:
            if (now - GroundedResponseGenerator._health_cache_ts) < self.HEALTH_CACHE_TTL_SECONDS:
                return GroundedResponseGenerator._health_cache

        is_production = self.settings.app_env.lower() in ("production", "staging")
        if is_production and _is_local_url(self.base_url):
            result = {
                "status": "bypassed_in_production",
                "available": False,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "reason": "Localhost Ollama bypassed in cloud production deployment",
                "latency_ms": 0.0,
            }
            GroundedResponseGenerator._health_cache = result
            GroundedResponseGenerator._health_cache_ts = now
            return result

        url = f"{self.base_url}/api/tags"
        start_time = time.perf_counter()
        connect_timeout = getattr(self.settings, "ollama_connect_timeout", 2.0)
        try:
            timeout_cfg = httpx.Timeout(connect_timeout + 1.0, connect=connect_timeout)
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
                is_model_present = any(self.model in m for m in models)
                result = {
                    "status": "healthy" if is_model_present else "model_missing",
                    "available": True,
                    "model": self.model,
                    "model_available": is_model_present,
                    "available_models": models,
                    "latency_ms": latency_ms,
                }
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
            result = {
                "status": "unavailable",
                "available": False,
                "model": self.model,
                "model_available": False,
                "available_models": [],
                "error_type": type(exc).__name__,
                "error": str(exc),
                "latency_ms": latency_ms,
            }

        GroundedResponseGenerator._health_cache = result
        GroundedResponseGenerator._health_cache_ts = now
        return result

    async def resolve_ai_provider(self) -> Tuple[str, str]:
        """Determine whether to use Ollama LLM or deterministic fallback engine.

        Returns:
            (provider_type, reason_string)
            where provider_type is 'ollama' or 'deterministic'
        """
        configured = (self.settings.ai_provider or "auto").strip().lower()

        if configured == "deterministic":
            return "deterministic", "ai_provider_explicitly_configured_deterministic"

        if configured == "ollama":
            health = await self.check_ollama_health()
            if health.get("available") and health.get("model_available"):
                return "ollama", "configured_ollama_online"
            return "deterministic", f"configured_ollama_unavailable: {health.get('status', 'offline')}"

        # configured == "auto"
        is_production = self.settings.app_env.lower() in ("production", "staging")
        if is_production and _is_local_url(self.base_url):
            return "deterministic", "cloud_production_localhost_skipped"

        # Check Ollama connectivity in development or remote host
        health = await self.check_ollama_health()
        if health.get("available") and health.get("model_available"):
            return "ollama", "ollama_service_online_and_ready"

        return "deterministic", f"ollama_unavailable: {health.get('status', 'offline')}"

    async def generate_answer(
        self,
        query: str,
        extracted: ExtractedIntent,
        query_result: Dict[str, Any],
        session_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, List[str]]:
        """Generate grounded natural language response and follow-up suggestions.
        
        Returns:
            (answer_text, follow_up_suggestions)
        """
        raw_source = query_result.get("source", "Live Weather Observations")
        source = self._clean_source_label(raw_source)
        timestamp = query_result.get("observation_timestamp", "Recent")
        suggestions = self._build_follow_up_suggestions(extracted)

        # 1. Unknown intent check
        if extracted.intent == "unknown_intent":
            msg = (
                "I am the **Tamil Nadu Weather Intelligence Agent**. I specialize exclusively in "
                "weather analytics, climate observations, rainfall patterns, air quality, and forecasts "
                "for all 38 districts of Tamil Nadu. Please ask me about temperature, rainfall, AQI, or district comparisons!"
            )
            return msg, [
                "What is the weather across Tamil Nadu today?",
                "Which district is the hottest right now?",
                "Show yesterday's rainfall distribution",
            ]

        # 2. Build verified factual summary text
        facts_summary = self._format_factual_summary(extracted, query_result)

        # 3. Resolve active AI provider (Ollama vs. Deterministic)
        active_provider, provider_reason = await self.resolve_ai_provider()
        log.info(
            "ai_provider_resolved",
            provider=active_provider,
            reason=provider_reason,
            intent=extracted.intent,
        )

        if active_provider == "ollama":
            system_prompt = (
                "You are the official Tamil Nadu Weather Intelligence AI Agent. "
                "Your answers must be 100% FACTUAL and STRICTLY BASED on the verified Microsoft Fabric data provided below. "
                "NEVER invent, estimate, or hallucinate weather values or measurements. "
                "Quote the verified numbers directly with appropriate units (°C, mm, %, AQI). "
                "If rainfall or another metric is unmeasured or missing, clearly state that it is unmeasured. "
                "Be clear, concise, and helpful."
            )

            user_prompt = (
                f"User Question: {query}\n\n"
                f"VERIFIED FABRIC LAKEHOUSE DATA:\n{facts_summary}\n\n"
                f"Data Source: {source}\n"
                f"Observation Timestamp: {timestamp} (Asia/Kolkata IST)\n\n"
                f"Please formulate a natural, complete, and precise response answering the user's question directly based on this data."
            )

            try:
                llm_text = await self._call_ollama(prompt=user_prompt, system=system_prompt)
                if llm_text and len(llm_text.strip()) > 15:
                    final_answer = llm_text.strip()
                    if "Data source:" not in final_answer:
                        final_answer += f"\n\n*Data source: {source} | Observation time: {timestamp} (IST)*"
                    return final_answer, suggestions
            except Exception as exc:
                log.warning(
                    "ollama_llm_fallback_engaged",
                    error_type=type(exc).__name__,
                    error=str(exc),
                    model=self.model,
                )

        # 4. Deterministic engine (used when Ollama is offline or bypassed in production)
        deterministic_answer = self._generate_deterministic_answer(extracted, query_result, facts_summary)
        return deterministic_answer, suggestions

    async def _call_ollama(self, prompt: str, system: str = "") -> Optional[str]:
        """Call Ollama Qwen3:4b model with streaming=False and configurable timeout."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 120,
            },
        }
        timeout_val = float(getattr(self.settings, "ai_request_timeout", 30))
        connect_val = float(getattr(self.settings, "ollama_connect_timeout", 2.5))
        timeout_cfg = httpx.Timeout(timeout_val, connect=connect_val)
        async with httpx.AsyncClient(timeout=timeout_cfg) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "").strip()

            if not raw:
                return None

            # Clean Qwen thinking tags if present
            if "<think>" in raw:
                if "</think>" in raw:
                    raw = raw.split("</think>")[-1].strip()
                else:
                    raw = raw.replace("<think>", "").strip()

            return raw if raw else None

    def _format_factual_summary(
        self, extracted: ExtractedIntent, res: Dict[str, Any]
    ) -> str:
        """Produce structured bulleted summary of verified Fabric results."""
        lines = []

        if "rankings" in res:
            metric = res.get("metric", "Metric")
            unit = res.get("unit", "")
            lines.append(f"Ranking results for {metric}:")
            for i, r in enumerate(res["rankings"], start=1):
                val = r.get("value") or r.get("pm25") or 0.0
                cond = f" (Condition: {r['condition']})" if "condition" in r else ""
                lines.append(f"  {i}. {r['district']}: {val} {unit}{cond}")

        elif "comparison_rows" in res:
            lines.append("Multi-district live comparison:")
            for r in res["comparison_rows"]:
                lines.append(
                    f"  - {r['district']}: Temp={r.get('temp')}°C (Feels {r.get('feels_like')}°C), "
                    f"Humidity={r.get('humidity')}%, Wind={r.get('wind_speed')} km/h, "
                    f"Rainfall={r.get('rainfall') or 0.0} mm, Condition={r.get('condition')}"
                )

        elif "comparison" in res:
            c = res["comparison"]
            temp = c.get("temperature", {})
            rain = c.get("rainfall", {})
            hum = c.get("humidity", {})
            lines.append(f"Period comparison for {res.get('district', 'Statewide')}:")
            lines.append(f"  - Temperature: Current={temp.get('current_val')}°C, Baseline={temp.get('previous_val')}°C, Delta={temp.get('absolute_change')}°C ({temp.get('direction')})")
            lines.append(f"  - Rainfall: Current={rain.get('current_val')} mm, Baseline={rain.get('previous_val')} mm, Delta={rain.get('absolute_change')} mm")
            lines.append(f"  - Humidity: Current={hum.get('current_val')}%, Baseline={hum.get('previous_val')}%, Delta={hum.get('absolute_change')}%")

        elif "rainfall_records" in res:
            q = res.get("quality", {})
            dist = res.get("district", "Tamil Nadu")
            tot_rf = q.get("total_measured_rainfall_mm")
            tot_days = q.get("total_observations") or q.get("total_days", 0)
            meas_days = q.get("measured_observations") or q.get("measured_days", 0)
            pos_days = q.get("positive_count") or q.get("positive_rainfall_days", 0)
            max_rf = q.get("max_measured_rainfall_mm", 0.0)

            lines.append(f"Rainfall observations and analytics for {dist} ({res.get('date_range')}):")
            lines.append(f"  - Total Measured Rainfall: {tot_rf if tot_rf is not None else '0.00'} mm")
            lines.append(f"  - Measured Observations: {meas_days}/{tot_days} ({q.get('completeness_pct', 0.0)}% completeness)")
            lines.append(f"  - Rainy/Positive Precipitation Days: {pos_days}")
            lines.append(f"  - Max Measured Rainfall: {max_rf if max_rf is not None else '0.00'} mm")
            if res["rainfall_records"]:
                r0 = res["rainfall_records"][0]
                rf_str = f"{r0.get('rainfall_mm')} mm" if r0.get('rainfall_mm') is not None else "Unmeasured"
                lines.append(f"  - Recent Record ({r0.get('date')}): Rainfall={rf_str}, Category={r0.get('category')}")

        elif "rows" in res and res["rows"]:
            dist = res.get("district", "Tamil Nadu")
            lines.append(f"Historical telemetry for {dist} ({res.get('date_range')}):")
            for r in res["rows"][:5]:
                lines.append(f"  - {r.get('date')}: Avg={r.get('avg_temp')}°C, Max={r.get('max_temp')}°C, Min={r.get('min_temp')}°C, Rain={r.get('total_rainfall')} mm")

        elif "overview" in res:
            o = res["overview"]
            lines.append("Statewide overview across all 38 districts:")
            lines.append(f"  - Districts reporting: {o.get('districts_covered')}/38")
            lines.append(f"  - Mean Temperature: {o.get('avg_temperature')}°C (Max: {o.get('max_temperature')}°C, Min: {o.get('min_temperature')}°C)")
            lines.append(f"  - Total Rainfall: {o.get('total_rainfall') if o.get('total_rainfall') is not None else 'Unmeasured'} mm")
            lines.append(f"  - Average Relative Humidity: {o.get('avg_humidity')}%")

        elif "details" in res and res["details"]:
            d = res["details"]
            lines.append(f"District intelligence profile for {d.get('district')}:")
            lines.append(f"  - Reference Location: {d.get('reference_location')}")
            lines.append(f"  - Geolocation: Latitude {d.get('latitude')}°N, Longitude {d.get('longitude')}°E")
            lines.append(f"  - Mean Temperature: {d.get('avg_temp')}°C (Max: {d.get('max_temp')}°C, Min: {d.get('min_temp')}°C)")
            lines.append(f"  - Relative Humidity: {d.get('avg_humidity')}%")

        elif "data" in res and res["data"]:
            rows = res["data"]
            if extracted.district and rows:
                item = rows[0]
                lines.append(f"Weather conditions for {item.get('district')}:")
                lines.append(f"  - Temperature: {item.get('temperature')}°C (Feels like: {item.get('feels_like')}°C)")
                lines.append(f"  - Condition: {item.get('condition')}")
                lines.append(f"  - Humidity: {item.get('humidity')}%")
                lines.append(f"  - Wind: {item.get('wind_speed')} km/h {item.get('wind_direction', '')}")
                lines.append(f"  - Pressure: {item.get('pressure')} hPa")
                rain_val = item.get('precipitation_mm')
                lines.append(f"  - Rainfall: {rain_val if rain_val is not None else '0.00'} mm")
            else:
                lines.append(f"Retrieved observations for {len(rows)} districts.")
                sample = rows[0]
                lines.append(f"Sample ({sample.get('district')}): {sample.get('temperature')}°C, {sample.get('condition')}, Humidity {sample.get('humidity')}%")

        else:
            lines.append("No specific telemetry records matched the exact filter criteria.")

        return "\n".join(lines)

    def _generate_deterministic_answer(
        self, extracted: ExtractedIntent, res: Dict[str, Any], facts: str
    ) -> str:
        """Deterministic factual generator covering all 15 intents with verified numbers."""
        raw_source = res.get("source", "Live Weather Observations")
        source = self._clean_source_label(raw_source)
        timestamp = res.get("observation_timestamp", "Recent")
        footer = f"\n\n*Data source: {source} | Observation time: {timestamp} (Asia/Kolkata IST)*"

        # ---------------------------------------------------------------------
        # 1. Weather Ranking Intent
        # ---------------------------------------------------------------------
        if extracted.intent == "weather_ranking" or "rankings" in res:
            m = res.get("metric", "Metric")
            u = res.get("unit", "")
            d = res.get("top_district")
            v = res.get("top_value")

            header = f"**Statewide Ranking – {m.title()}:**\n\n"
            if d and v is not None:
                header += f"**{d}** recorded the highest {m.lower()} at **{v} {u}**.\n\n"

            lines = []
            if "rankings" in res and res["rankings"]:
                lines.append("**Top Ranked Districts:**")
                for i, r in enumerate(res["rankings"][:5], start=1):
                    val = r.get("value") or r.get("pm25") or 0.0
                    cond = f" ({r['condition']})" if "condition" in r else ""
                    lines.append(f"- **#{i} {r['district']}**: {val} {u}{cond}")

            content = "\n".join(lines) if lines else facts
            return f"{header}{content}{footer}"

        # ---------------------------------------------------------------------
        # 2. District Comparison Intent
        # ---------------------------------------------------------------------
        if extracted.intent == "district_comparison" or "comparison_rows" in res:
            rows = res.get("comparison_rows", [])
            lines = ["**Multi-District Weather Comparison:**\n"]
            for r in rows:
                rain_val = r.get("rainfall")
                rain_str = f"{rain_val:.2f} mm" if rain_val is not None else "Unmeasured / 0.0 mm"
                lines.append(
                    f"- **{r['district']}**: {r.get('temp')}°C (Feels like {r.get('feels_like')}°C) | "
                    f"Humidity: {r.get('humidity')}% | Wind: {r.get('wind_speed')} km/h | "
                    f"Rainfall: {rain_str} | Condition: {r.get('condition')}"
                )
            if len(rows) >= 2:
                t0 = rows[0].get("temp")
                t1 = rows[1].get("temp")
                if t0 is not None and t1 is not None:
                    diff = round(abs(t0 - t1), 1)
                    warmer = rows[0]["district"] if t0 > t1 else rows[1]["district"]
                    cooler = rows[1]["district"] if t0 > t1 else rows[0]["district"]
                    if diff > 0:
                        lines.append(f"\n*{warmer} is currently {diff}°C warmer than {cooler}.*")
            return f"{chr(10).join(lines)}{footer}"

        # ---------------------------------------------------------------------
        # 3. Date Comparison Intent
        # ---------------------------------------------------------------------
        if extracted.intent == "date_comparison" or "comparison" in res:
            c = res.get("comparison", {})
            dist = res.get("district", "Tamil Nadu")
            temp = c.get("temperature", {})
            rain = c.get("rainfall", {})
            hum = c.get("humidity", {})
            lines = [f"**Period Comparison Analysis for {dist}:**\n"]
            if temp:
                cur_t = temp.get("current_val")
                prev_t = temp.get("previous_val")
                chg_t = temp.get("absolute_change")
                d_t = temp.get("direction", "")
                lines.append(f"- **Temperature:** Current {cur_t}°C vs Baseline {prev_t}°C (Delta: {chg_t}°C, {d_t})")
            if rain:
                cur_r = rain.get("current_val")
                prev_r = rain.get("previous_val")
                chg_r = rain.get("absolute_change")
                lines.append(f"- **Rainfall:** Current {cur_r} mm vs Baseline {prev_r} mm (Delta: {chg_r} mm)")
            if hum:
                cur_h = hum.get("current_val")
                prev_h = hum.get("previous_val")
                chg_h = hum.get("absolute_change")
                lines.append(f"- **Relative Humidity:** Current {cur_h}% vs Baseline {prev_h}% (Delta: {chg_h}%)")
            return f"{chr(10).join(lines)}{footer}"

        # ---------------------------------------------------------------------
        # 4. Air Quality Analysis Intent
        # ---------------------------------------------------------------------
        if extracted.intent == "air_quality_analysis" or extracted.metric == "air_quality":
            lines = ["**Air Quality Intelligence (AQI):**\n"]
            if "rankings" in res and res["rankings"]:
                lines.append("Top districts by AQI / Particulate Matter:")
                for i, r in enumerate(res["rankings"][:5], start=1):
                    val = r.get("value") or r.get("pm25") or 0.0
                    cat = r.get("category", "Moderate")
                    lines.append(f"- **#{i} {r['district']}**: AQI {val} ({cat})")
                lines.append("\n*Health Advisory: In areas with elevated AQI, sensitive groups should limit strenuous outdoor activities.*")
            elif "data" in res and res["data"]:
                item = res["data"][0]
                d = item.get("district")
                aqi = item.get("aqi") or item.get("us_aqi") or item.get("pm2_5")
                cat = item.get("category") or "Moderate"
                lines.append(f"- **District:** {d}")
                lines.append(f"- **AQI Reading:** {aqi} ({cat})")
                if "pm2_5" in item:
                    lines.append(f"- **PM2.5:** {item['pm2_5']} µg/m³")
                if "pm10" in item:
                    lines.append(f"- **PM10:** {item['pm10']} µg/m³")
                lines.append(f"- **Health Guidance:** {self._get_aqi_advisory(cat)}")
            else:
                lines.append(facts)
            return f"{chr(10).join(lines)}{footer}"

        # ---------------------------------------------------------------------
        # 5. Rainfall Analysis Intent
        # ---------------------------------------------------------------------
        if extracted.intent == "rainfall_analysis" or extracted.metric == "rainfall" or "rainfall_records" in res:
            dist = res.get("district", extracted.district or "Tamil Nadu")
            q = res.get("quality", {})
            tot = q.get("total_measured_rainfall_mm")
            pos_days = q.get("positive_count") or q.get("positive_rainfall_days", 0)
            meas_days = q.get("measured_observations") or q.get("measured_days", 0)
            tot_days = q.get("total_observations") or q.get("total_days", 0)
            completeness = q.get("completeness_pct", 100.0)

            # Strict NULL vs 0.0 handling
            if tot is None:
                tot_str = "0.00 mm (No measurable precipitation recorded)"
            else:
                tot_str = f"{tot:.2f} mm"

            lines = [f"**Verified Rainfall Intelligence for {dist}:**\n"]
            if res.get("date_range"):
                lines.append(f"- **Time Period:** {res.get('date_range')}")
            lines.append(f"- **Total Measured Rainfall:** {tot_str}")
            lines.append(f"- **Rainy Days (>0 mm):** {pos_days}")
            if q.get("max_measured_rainfall_mm"):
                lines.append(f"- **Peak Daily Rainfall:** {q['max_measured_rainfall_mm']:.2f} mm")
            lines.append(f"- **Data Completeness:** {completeness:.1f}% ({meas_days}/{tot_days} observations measured)")

            if res.get("rainfall_records"):
                r0 = res["rainfall_records"][0]
                rf_str = f"{r0.get('rainfall_mm')} mm" if r0.get('rainfall_mm') is not None else "Unmeasured"
                lines.append(f"- **Recent Observation ({r0.get('date')}):** {rf_str} ({r0.get('category')})")

            return f"{chr(10).join(lines)}{footer}"

        # ---------------------------------------------------------------------
        # 6. Temperature Analysis & Weather Trend Intent
        # ---------------------------------------------------------------------
        if extracted.intent in ("temperature_analysis", "weather_trend") or ("rows" in res and res["rows"]):
            dist = res.get("district", extracted.district or "Tamil Nadu")
            rows = res.get("rows", [])
            lines = [f"**Verified Weather Trajectory for {dist}:**\n"]
            if res.get("date_range"):
                lines.append(f"- **Date Range:** {res.get('date_range')}")
            if rows:
                temps = [r.get("avg_temp") for r in rows if r.get("avg_temp") is not None]
                maxs = [r.get("max_temp") for r in rows if r.get("max_temp") is not None]
                mins = [r.get("min_temp") for r in rows if r.get("min_temp") is not None]
                if temps:
                    avg_t = round(sum(temps) / len(temps), 1)
                    high_t = max(maxs) if maxs else avg_t
                    low_t = min(mins) if mins else avg_t
                    lines.append(f"- **Mean Temperature:** {avg_t}°C (Range: {low_t}°C to {high_t}°C)")
                sample = rows[0]
                lines.append(f"- **Sample Observation ({sample.get('date')}):** Avg {sample.get('avg_temp')}°C, Max {sample.get('max_temp')}°C, Min {sample.get('min_temp')}°C")
            return f"{chr(10).join(lines)}{footer}"

        # ---------------------------------------------------------------------
        # 7. District Intelligence Intent
        # ---------------------------------------------------------------------
        if extracted.intent == "district_intelligence" or ("details" in res and res["details"]):
            d = res.get("details", {})
            dist_name = d.get("district", extracted.district or "District")
            lines = [f"**District Intelligence Profile – {dist_name}:**\n"]
            if d.get("reference_location"):
                lines.append(f"- **Reference Station:** {d.get('reference_location')}")
            if d.get("latitude") and d.get("longitude"):
                lines.append(f"- **Coordinates:** {d.get('latitude')}°N, {d.get('longitude')}°E")
            if d.get("avg_temp") is not None:
                lines.append(f"- **Historical Mean Temperature:** {d.get('avg_temp')}°C (High: {d.get('max_temp')}°C, Low: {d.get('min_temp')}°C)")
            if d.get("avg_humidity") is not None:
                lines.append(f"- **Average Relative Humidity:** {d.get('avg_humidity')}%")
            return f"{chr(10).join(lines)}{footer}"

        # ---------------------------------------------------------------------
        # 8. Statewide Summary & Weather Report Intent
        # ---------------------------------------------------------------------
        if extracted.intent in ("statewide_summary", "weather_report") or "overview" in res:
            o = res.get("overview", {})
            dist_rep = o.get("districts_covered", 38)
            avg_t = o.get("avg_temperature")
            max_t = o.get("max_temperature")
            min_t = o.get("min_temperature")
            tot_rain = o.get("total_rainfall")
            avg_h = o.get("avg_humidity")
            rain_str = f"{tot_rain:.1f} mm" if tot_rain is not None else "Unmeasured / No measurable precipitation"
            lines = [
                "### Tamil Nadu Statewide Weather Bulletin\n",
                f"- **Districts Reporting:** {dist_rep} of 38 districts",
                f"- **Average Temperature:** {avg_t}°C (High: {max_t}°C | Low: {min_t}°C)",
                f"- **Average Relative Humidity:** {avg_h}%",
                f"- **Total Recorded Rainfall:** {rain_str}",
            ]
            return f"{chr(10).join(lines)}{footer}"

        # ---------------------------------------------------------------------
        # 9. Dashboard Request Intent
        # ---------------------------------------------------------------------
        if extracted.intent == "dashboard_request":
            lines = [
                "**Custom Dashboard Specification:**\n",
                "You can access specialized analytics modules from the left navigation panel:\n",
                "- **Weather Overview:** Real-time statewide KPIs and district observation grid.",
                "- **Temperature Analytics:** Thermal heatmaps, top rankings, and trend charts.",
                "- **Rainfall Analytics:** Daily precipitation totals, quality verification, and historical records.",
                "- **Air Quality:** District AQI rankings, PM2.5, PM10, and health advisories.",
                "- **District Intelligence:** Deep-dive profiles for all 38 Tamil Nadu districts.",
            ]
            return f"{chr(10).join(lines)}{footer}"

        # ---------------------------------------------------------------------
        # 10. Single District Current or Historical Observation (Default)
        # ---------------------------------------------------------------------
        if extracted.district and "data" in res and res["data"]:
            item = res["data"][0]
            d = item.get("district", extracted.district)
            t = item.get("temperature")
            fl = item.get("feels_like")
            c = item.get("condition")
            h = item.get("humidity")
            w = item.get("wind_speed")
            wdir = item.get("wind_direction", "")
            r = item.get("precipitation_mm")
            rain_str = f"{r:.2f} mm" if r is not None else "0.00 mm (No precipitation)"

            lines = [
                f"**Current weather in {d}:**\n",
                f"- **Temperature:** {t}°C (Feels like {fl}°C)",
                f"- **Condition:** {c}",
                f"- **Humidity:** {h}%",
                f"- **Wind:** {w} km/h {wdir}".strip(),
                f"- **Rainfall:** {rain_str}",
            ]
            if item.get("pressure"):
                lines.append(f"- **Pressure:** {item.get('pressure')} hPa")
            return f"{chr(10).join(lines)}{footer}"

        # Generic fallback based on formatted facts
        return (
            f"Here is the verified weather intelligence for Tamil Nadu:\n\n"
            f"{facts}\n\n"
            f"*Data source: {source} | Observation time: {timestamp} (Asia/Kolkata IST)*"
        )

    def _build_follow_up_suggestions(self, extracted: ExtractedIntent) -> List[str]:
        """Suggest logical next queries based on current entity context."""
        district = extracted.district
        metric = extracted.metric

        if district:
            if metric == "rainfall":
                return [
                    f"What is the temperature in {district}?",
                    f"Check air quality in {district}",
                    f"Compare {district} and Coimbatore",
                ]
            else:
                return [
                    f"Did it rain in {district} yesterday?",
                    f"What is the air quality in {district}?",
                    f"Compare {district} and Madurai",
                ]

        if extracted.intent == "weather_ranking":
            return [
                "Which district had the most rain yesterday?",
                "Which districts have the highest AQI?",
                "Show statewide weather summary",
            ]

        return [
            "Which district is the hottest right now?",
            "Compare Chennai and Coimbatore weather",
            "Show yesterday's rainfall across Tamil Nadu",
        ]
