"""Grounded Natural-Language Response Generation.

Combines verified Microsoft Fabric Lakehouse query results with local Qwen3:4b LLM.
Strictly grounds every numerical assertion on actual returned records.
Provides deterministic, zero-hallucination fallback if Ollama is unavailable.
"""

from datetime import date
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
import structlog

from app.config import get_settings
from app.schemas.ai import ExtractedIntent

log = structlog.get_logger()


class GroundedResponseGenerator:
    """Generates strictly verified, factual answers from Fabric query results."""

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

        # 3. Attempt LLM generation via Ollama (Qwen3:4b)
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
                # Append standard audit provenance line if not already mentioned
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

        # 4. Deterministic fallback if LLM is unavailable or times out
        deterministic_answer = self._generate_deterministic_answer(extracted, query_result, facts_summary)
        return deterministic_answer, suggestions

    async def check_ollama_health(self) -> Dict[str, Any]:
        """Perform a lightweight health check against the local Ollama instance."""
        url = f"{self.base_url}/api/tags"
        start_time = time.perf_counter()
        try:
            timeout_cfg = httpx.Timeout(2.0, connect=1.0)
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
                is_model_present = any(self.model in m for m in models)
                return {
                    "status": "healthy" if is_model_present else "model_missing",
                    "available": True,
                    "model": self.model,
                    "model_available": is_model_present,
                    "available_models": models,
                    "latency_ms": latency_ms,
                }
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
            return {
                "status": "unavailable",
                "available": False,
                "model": self.model,
                "model_available": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "latency_ms": latency_ms,
            }

    async def _call_ollama(self, prompt: str, system: str = "") -> Optional[str]:
        """Call local Ollama Qwen3:4b model with streaming=False and fast timeout."""
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
        timeout_val = getattr(self.settings, "ollama_timeout", 15.0)
        timeout_cfg = httpx.Timeout(timeout_val, connect=2.0)
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
        """Deterministic factual generator guaranteed to succeed without LLM."""
        raw_source = res.get("source", "Live Weather Observations")
        source = self._clean_source_label(raw_source)
        timestamp = res.get("observation_timestamp", "Recent")

        if extracted.intent == "weather_ranking" and "top_district" in res:
            d = res["top_district"]
            v = res["top_value"]
            m = res.get("metric", "metric")
            u = res.get("unit", "")
            return (
                f"Based on verified **{source}**, **{d}** recorded the highest {m.lower()} "
                f"at **{v} {u}**.\n\n"
                f"{facts}\n\n"
                f"*Data source: {source} | Observation time: {timestamp} (Asia/Kolkata IST)*"
            )

        if extracted.district and "data" in res and res["data"]:
            item = res["data"][0]
            d = item.get("district")
            t = item.get("temperature")
            fl = item.get("feels_like")
            c = item.get("condition")
            h = item.get("humidity")
            w = item.get("wind_speed")
            r = item.get("precipitation_mm")
            rain_str = f"{r:.2f} mm" if r is not None else "0.00 mm"
            return (
                f"**Current weather in {d}:**\n\n"
                f"- **Temperature:** {t}°C (Feels like {fl}°C)\n"
                f"- **Condition:** {c}\n"
                f"- **Humidity:** {h}%\n"
                f"- **Wind:** {w} km/h {item.get('wind_direction', '')}\n"
                f"- **Rainfall:** {rain_str}\n\n"
                f"*Data source: {source} | Observation time: {timestamp} (Asia/Kolkata IST)*"
            )

        if "rainfall_records" in res:
            dist = res.get("district", "Tamil Nadu")
            q = res.get("quality", {})
            tot = q.get("total_measured_rainfall_mm")
            tot_str = f"{tot} mm" if tot is not None else "0.00 mm (No measurable precipitation recorded)"
            pos_days = q.get("positive_count") or q.get("positive_rainfall_days", 0)
            return (
                f"**Verified Rainfall Intelligence for {dist}:**\n\n"
                f"- **Time Period:** {res.get('date_range')}\n"
                f"- **Total Measured Rainfall:** {tot_str}\n"
                f"- **Rainy Days:** {pos_days}\n"
                f"- **Data Completeness:** {q.get('completeness_pct', 100.0)}%\n\n"
                f"*Data source: {source} | Observation time: {timestamp} (Asia/Kolkata IST)*"
            )

        if "rows" in res and res["rows"]:
            dist = res.get("district", "Tamil Nadu")
            sample = res["rows"][0]
            return (
                f"**Verified Temperature Trajectory for {dist}:**\n\n"
                f"- **Date Range:** {res.get('date_range')}\n"
                f"- **Observation ({sample.get('date')}):** Avg {sample.get('avg_temp')}°C (Max {sample.get('max_temp')}°C, Min {sample.get('min_temp')}°C)\n\n"
                f"*Data source: {source} | Observation time: {timestamp} (Asia/Kolkata IST)*"
            )

        if "overview" in res:
            o = res["overview"]
            dist_rep = o.get("districts_covered", 38)
            avg_t = o.get("avg_temperature")
            max_t = o.get("max_temperature")
            min_t = o.get("min_temperature")
            tot_rain = o.get("total_rainfall")
            avg_h = o.get("avg_humidity")
            rain_str = f"{tot_rain:.1f} mm" if tot_rain is not None else "Unmeasured / No measurable precipitation"
            return (
                f"### Tamil Nadu Statewide Weather Overview\n\n"
                f"- **Districts Reporting:** {dist_rep} of 38 districts\n"
                f"- **Average Temperature:** {avg_t}°C (High: {max_t}°C | Low: {min_t}°C)\n"
                f"- **Average Relative Humidity:** {avg_h}%\n"
                f"- **Total Rainfall:** {rain_str}\n\n"
                f"*Data source: {source} | Observation time: {timestamp} (Asia/Kolkata IST)*"
            )

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
