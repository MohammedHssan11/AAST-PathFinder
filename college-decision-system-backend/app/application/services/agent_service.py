import json
import logging
from collections.abc import Mapping
import google.generativeai as genai
from google.generativeai.types import content_types
from pydantic import ValidationError
from decimal import Decimal
import re

from app.config.settings import settings
from app.application.use_cases.recommend_programs import (
    RecommendProgramsUseCase,
    RecommendProgramsRequest,
)
from app.infrastructure.db.repositories.chat_repo import ChatRepository

logger = logging.getLogger(__name__)

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY.get_secret_value())


class AgentService:
    def __init__(
        self,
        recommend_use_case: RecommendProgramsUseCase,
        chat_repo: ChatRepository,
    ) -> None:
        self.recommend_use_case = recommend_use_case
        self.chat_repo = chat_repo
        
        # Tool definition
        self.get_recommendations_tool = {
            "function_declarations": [
                {
                    "name": "get_recommendations",
                    "description": "Fetches ranked college programs based on student input. ONLY use this tool for recommendations. Do not guess scores or fees.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "certificate_type": {
                                "type": "STRING",
                                "description": "Raw certificate label from the client, e.g., 'Egyptian Thanaweya Amma (Science)', 'IGCSE', 'American Diploma'."
                            },
                            "high_school_percentage": {
                                "type": "NUMBER",
                                "description": "Student percentage or score on a 0-100 scale."
                            },
                            "student_group": {
                                "type": "STRING",
                                "description": "Student fee group, either 'supportive_states' or 'other_states'."
                            },
                            "budget": {
                                "type": "NUMBER",
                                "description": "Optional semester budget in USD-equivalent values."
                            },
                            "preferred_branch": {
                                "type": "STRING",
                                "description": "Optional preferred branch or campus label."
                            },
                            "preferred_city": {
                                "type": "STRING",
                                "description": "Optional preferred city."
                            },
                            "interests": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                                "description": "List of student interests like AI, business, engineering."
                            },
                            "track_type": {
                                "type": "STRING",
                                "description": "Fee track used by the lookup layer, default 'regular'."
                            }
                        },
                    },
                }
            ]
        }

        self.system_instruction = (
            "You are an Expert AAST Academic Consultant. Your tone is professional, encouraging, and data-driven.\n"
            "Your main task is to help the student find the best college program.\n"
            "Important: Student interests account for 60% of the matching score. Always prioritize programs that match their stated interests.\n"
            "### International Partnerships:\n"
            "- The College of Artificial Intelligence (CAI) in Alamein is a prestigious international partnership with Universitat Autònoma de Barcelona (UAB), Spain. Mention this for AI programs in Alamein.\n"
            "### Track Eligibility:\n"
            "- Egyptian Science (علمي علوم) students CANNOT join Engineering. They are eligible for Computing, AI, Pharmacy, Dentistry, and Medicine.\n"
            "- Egyptian Math (علمي رياضة) students CANNOT join Medicine, Pharmacy, or Dentistry. They are eligible for Engineering, Computing, and AI.\n"
            "If a student asks for a blocked program, explain why based on their track.\n"
            "### Scoring Explanation:\n"
            "When results are returned via get_recommendations, you must explain the `score_breakdown` in natural language.\n"
            "If a program is within the student's budget (e.g., $10,000), highlight that the Affordability Score is high, which significantly boosts their match score.\n"
            "### Confidence Disclaimer Rule:\n"
            "If the top recommendation has a `confidence_level` of 'Low' or a matching `score` below 70, you MUST include a disclaimer like: "
            "'Note: These matches are based on partial data or lower alignment scores. I recommend visiting the campus or contacting AAST for more details.'\n"
            "Do NOT invent or guess scores or fees. Always rely on the data returned by the tool."
        )
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=self.get_recommendations_tool,
            system_instruction=self.system_instruction,
        )

    def _safe_decimal(self, val):
        if val is None:
            return None
        try:
            if isinstance(val, (int, float)):
                return Decimal(str(val))
            s = str(val).strip()
            # Handle percentage and currency symbols
            s = re.sub(r'[^0-9.]', '', s)
            if not s:
                return None
            return Decimal(s)
        except Exception:
            return None

    def _to_plain_obj(self, obj):
        if obj is None:
            return None
        if isinstance(obj, (int, float, str, bool)):
            return obj
        
        # Handle dictionary-like objects first (including Protobuf Struct/Map)
        if isinstance(obj, (dict, Mapping)):
            return {str(k): self._to_plain_obj(v) for k, v in obj.items()}
            
        if isinstance(obj, (list, tuple)):
            return [self._to_plain_obj(x) for x in obj]
            
        if hasattr(obj, "to_dict"):
            try:
                return self._to_plain_obj(obj.to_dict())
            except Exception:
                pass
        
        # Check if iterable (for RepeatedComposite or other sequences)
        # BUT skip if it's already string-like or handled
        try:
            # We already handled Mapping and list/tuple above.
            # This is for other iterables like RepeatedComposite.
            return [self._to_plain_obj(x) for x in iter(obj)]
        except (TypeError, AttributeError):
            pass
            
        return str(obj)

    def process_message(self, session_id: str, message: str) -> tuple[str, list[dict]]:
        try:
            return self._process_message_internal(session_id, message)
        except Exception as e:
            logger.exception(f"Critical error in AgentService for session {session_id}")
            # Silently handle and return a graceful message to avoid 500
            return f"I apologize, but I encountered an internal error while processing your request. Could you try rephrasing? (Error: {str(e)})", []

    def _process_message_internal(self, session_id: str, message: str) -> tuple[str, list[dict]]:
        # 1. Store user message
        self.chat_repo.add_message(session_id=session_id, role="user", content=message)

        # 2. Build history for Gemini
        db_history = self.chat_repo.get_history(session_id=session_id, limit=6)
        
        formatted_history = []
        for msg in db_history:
            if msg.role == "user":
                formatted_history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "model":
                parts = []
                if msg.content:
                    parts.append(msg.content)
                if msg.tool_calls:
                    for call in msg.tool_calls:
                        if "function_call" in call:
                            # It's a function call from model
                            parts.append({
                                "function_call": {
                                    "name": call["function_call"]["name"],
                                    "args": call["function_call"]["args"]
                                }
                            })
                        elif "function_response" in call:
                            # It's a function response back to model
                            parts.append({
                                "function_response": {
                                    "name": call["function_response"]["name"],
                                    "response": call["function_response"]["response"]
                                }
                            })
                formatted_history.append({"role": "model", "parts": parts})
                
        # To avoid passing complex structured history if it breaks Gemini, 
        # let's just use simple text history for context but start a fresh chat for tools to ensure reliable behavior.
        # But we want context. Let's send the text history as system instructions or pre-prompt.
        
        chat = self.model.start_chat()
        
        # Inject context (hack: we just send the previous messages to initialize the chat state)
        # Actually Google's start_chat takes `history` as a list of ContentDicts.
        chat_history_for_gemini = []
        for msg in db_history[:-1]: # exclude the latest message which we just added
            if msg.role == "user":
                chat_history_for_gemini.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "model":
                if msg.content:
                    chat_history_for_gemini.append({"role": "model", "parts": [msg.content]})
                    
        # Replace simple chat with history initialized chat if history exists
        if chat_history_for_gemini:
            chat = self.model.start_chat(history=chat_history_for_gemini)

        # 3. Send message to model
        response = chat.send_message(message)

        recommendations_data = []
        final_reply = ""
        tool_calls_record = []

        # 4. Check if it triggered a tool
        if getattr(response, 'function_call', None) or any(part.function_call for part in response.parts):
            # Find the function call
            fc = response.function_call if getattr(response, 'function_call', None) else None
            if not fc:
                for part in response.parts:
                    if part.function_call:
                        fc = part.function_call
                        break
                        
            if fc and fc.name == "get_recommendations":
                args = self._to_plain_obj(fc.args)
                
                tool_calls_record.append({"function_call": {"name": fc.name, "args": args}})
                
                # Execute engine
                try:
                    req = RecommendProgramsRequest(
                        certificate_type=args.get("certificate_type"),
                        high_school_percentage=self._safe_decimal(args.get("high_school_percentage")),
                        student_group=args.get("student_group") or "supportive_states",
                        budget=self._safe_decimal(args.get("budget")),
                        preferred_branch=args.get("preferred_branch"),
                        preferred_city=args.get("preferred_city"),
                        interests=args.get("interests", []),
                        track_type=args.get("track_type", "regular"),
                        max_results=5,
                        min_results=3,
                    )
                    
                    engine_result = self.recommend_use_case.execute(req)
                    
                    # Truncate and prep data for LLM
                    summary_result = {
                        "total_candidates": engine_result.total_candidates_considered,
                        "recommendations": [],
                        "excluded_programs": [
                            {"program_name": ep.program_name, "college_name": ep.college_name, "reason": ep.reason}
                            for ep in engine_result.excluded_programs
                        ][:10] # limit to avoid blown up context
                    }
                    
                    for rec in engine_result.recommendations:
                        rec_dict = {
                            "program_name": rec.program_name,
                            "college_name": rec.college_name,
                            "score": rec.score,
                            "confidence_level": rec.confidence_level,
                            "score_breakdown": rec.score_breakdown,
                            "estimated_semester_fee": float(rec.estimated_semester_fee) if rec.estimated_semester_fee else None,
                            "affordability_label": rec.affordability_label,
                            "explanation_summary": rec.explanation_summary
                        }
                        summary_result["recommendations"].append(rec_dict)
                        # We also need to build the full recommendation schema to return to the frontend
                        # But for now we'll just mock it or map it. The UI expects the full schema.
                        
                        full_rec = {
                            "program_id": rec.program_id,
                            "program_name": rec.program_name,
                            "college_id": rec.college_id,
                            "college_name": rec.college_name,
                            "confidence_level": rec.confidence_level,
                            "score": rec.score,
                            "recommendation_score": rec.recommendation_score,
                            "match_type": rec.match_type,
                            "fee_category": rec.fee_category,
                            "fee_category_confidence": rec.fee_category_confidence,
                            "fee_resolution_reason": rec.fee_resolution_reason,
                            "matched_fee_category": rec.matched_fee_category,
                            "estimated_semester_fee": float(rec.estimated_semester_fee) if rec.estimated_semester_fee else None,
                            "additional_recurring_fees": float(rec.additional_recurring_fees) if rec.additional_recurring_fees else None,
                            "additional_one_time_fees": float(rec.additional_one_time_fees) if rec.additional_one_time_fees else None,
                            "additional_one_time_fees_total": float(rec.additional_one_time_fees_total) if rec.additional_one_time_fees_total else None,
                            "additional_one_time_fees_breakdown": [],
                            "one_time_fees": float(rec.one_time_fees) if rec.one_time_fees else None,
                            "currency": rec.currency,
                            "academic_year": rec.academic_year,
                            "fee_mode": rec.fee_mode,
                            "fee_match_level": rec.fee_match_level,
                            "fee_match_source": rec.fee_match_source,
                            "fee_match_confidence": rec.fee_match_confidence,
                            "tuition_unavailable": rec.tuition_unavailable,
                            "fee_data_incomplete": rec.fee_data_incomplete,
                            "used_college_fallback": rec.used_college_fallback,
                            "warnings": rec.warnings,
                            "affordability_label": rec.affordability_label,
                            "training_intensity": rec.training_intensity,
                            "derived_training_intensity_label": rec.derived_training_intensity_label,
                            "score_breakdown": rec.score_breakdown,
                            "explanation_summary": rec.explanation_summary,
                            "matched_interests": rec.matched_interests,
                            "fee_resolution_note": rec.fee_resolution_note,
                            "fee_details": {
                                "fee_category": rec.fee_details.fee_category,
                                "fee_category_confidence": rec.fee_details.fee_category_confidence,
                                "fee_resolution_reason": rec.fee_details.fee_resolution_reason,
                                "fee_match_level": rec.fee_details.fee_match_level,
                                "fee_match_source": rec.fee_details.fee_match_source,
                                "fee_match_confidence": rec.fee_details.fee_match_confidence,
                                "estimated_semester_fee": float(rec.fee_details.estimated_semester_fee) if rec.fee_details.estimated_semester_fee else None,
                                "recurring_total": float(rec.fee_details.recurring_total) if rec.fee_details.recurring_total else None,
                                "additional_recurring_fees_total": float(rec.fee_details.additional_recurring_fees_total) if rec.fee_details.additional_recurring_fees_total else None,
                                "additional_recurring_fees_breakdown": [],
                                "additional_one_time_fees_total": float(rec.fee_details.additional_one_time_fees_total) if rec.fee_details.additional_one_time_fees_total else None,
                                "additional_one_time_fees_breakdown": [],
                                "unknown_frequency_fees_total": float(rec.fee_details.unknown_frequency_fees_total) if rec.fee_details.unknown_frequency_fees_total else None,
                                "unknown_frequency_fees_breakdown": [],
                                "currency": rec.fee_details.currency,
                                "academic_year": rec.fee_details.academic_year,
                                "fee_mode": rec.fee_details.fee_mode,
                                "tuition_unavailable": rec.fee_details.tuition_unavailable,
                                "fee_data_incomplete": rec.fee_details.fee_data_incomplete,
                                "used_college_fallback": rec.fee_details.used_college_fallback,
                                "warnings": rec.fee_details.warnings,
                            },
                            "decision_data_completeness": {
                                "has_profile": rec.decision_data_completeness.has_profile,
                                "has_training_data": rec.decision_data_completeness.has_training_data,
                                "has_employment_data": rec.decision_data_completeness.has_employment_data,
                                "has_admission_data": rec.decision_data_completeness.has_admission_data,
                                "completeness_score": rec.decision_data_completeness.completeness_score,
                                "missing_fields": rec.decision_data_completeness.missing_fields,
                                "warnings": rec.decision_data_completeness.warnings,
                            },
                            "location_note": rec.location_note
                        }
                        recommendations_data.append(full_rec)

                    # Send results back to LLM using valid Part format
                    tool_calls_record.append({"function_response": {"name": fc.name, "response": summary_result}})
                    
                    response = chat.send_message(
                        content_types.to_part({
                            "function_response": {
                                "name": "get_recommendations",
                                "response": {"result": summary_result}
                            }
                        })
                    )
                    
                    if response.candidates and response.candidates[0].content.parts:
                        final_reply = response.text
                    else:
                        final_reply = "I've processed the data, but I'm having trouble generating a final summary. However, you can see the recommendations below."
                        
                    if len(engine_result.recommendations) == 0:
                        final_reply = "Unfortunately, you don't meet the hard requirements for any current programs."
                except Exception as e:
                    logger.error(f"Error executing recommend_use_case: {e}")
                    final_reply = "I apologize, but I encountered an error while searching for recommendations. Let's try adjusting your criteria slightly."
        else:
            if response.candidates and response.candidates[0].content.parts:
                final_reply = response.text
            else:
                final_reply = "I'm sorry, I couldn't generate a response. Please try again."
            
        # 5. Store model reply
        self.chat_repo.add_message(
            session_id=session_id, 
            role="model", 
            content=final_reply, 
            tool_calls=tool_calls_record if tool_calls_record else None
        )

        return final_reply, recommendations_data
