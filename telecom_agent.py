import os
import re
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from dotenv import load_dotenv

# LangChain and LangGraph imports
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Import database module
import telecom_db

# Load environment variables
load_dotenv()

# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    customer_id: str
    category: str  # 'billing', 'technical_support', 'plan_upgrade', 'general'
    diagnostics_run: bool
    router_status: Dict[str, Any]
    retry_count: int
    current_fix: str
    agent_logs: List[str]
    solution_found: bool

# Simple custom Mock LLM for fallback when API key is missing
class MockTelecomLLM(BaseChatModel):
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Extract the user's latest query
        user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_msg = m.content.lower()
                break
        
        # Categorize query
        if any(w in user_msg for w in ["bill", "charge", "pay", "cost", "fee", "money"]):
            category = "billing"
            response_content = (
                "CATEGORY: billing\n"
                "REASONING: The customer has a question about their monthly invoice, fees, or data charges.\n"
                "RESPONSE: I see you have a query about your bill. I've retrieved your latest bill of $124.50. "
                "You have a standard plan cost of $85.00, a late payment fee of $10.00, and a data overage charge of $29.50. "
                "I can assist you in waiving the late fee if this is your first time, or review upgrade options to avoid future overages. Which would you prefer?"
            )
        elif any(w in user_msg for w in ["slow", "internet", "wifi", "disconnect", "router", "broadband", "speed", "offline"]):
            category = "technical_support"
            response_content = (
                "CATEGORY: technical_support\n"
                "REASONING: Customer reports poor connection speed or router issues requiring remote troubleshooting.\n"
                "RESPONSE: I understand you are experiencing network speed or connectivity issues. Let me initiate a remote "
                "diagnostic check on your broadband modem/router to analyze signal levels and packet loss."
            )
        elif any(w in user_msg for w in ["plan", "upgrade", "change", "cheaper", "tier", "giga", "speed upgrade"]):
            category = "plan_upgrade"
            response_content = (
                "CATEGORY: plan_upgrade\n"
                "REASONING: The customer wants to change their subscription, speed tier, or upgrade their services.\n"
                "RESPONSE: I can definitely help you optimize your subscription plan. Currently, we offer GigaFiber Ultra (1Gbps) for $80/mo, "
                "Fiber Medium (500Mbps) for $65/mo, and Fiber Basic (300Mbps) for $50/mo. Which speed tier fits your requirements?"
            )
        else:
            category = "general"
            response_content = (
                "CATEGORY: general\n"
                "REASONING: General greeting or query outside billing, technical support, and upgrades.\n"
                "RESPONSE: Hello! Thank you for contacting Telecom Support. I can help you troubleshoot technical issues, "
                "analyze your monthly bill, or find a better subscription plan. How can I help you today?"
            )
            
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response_content))])

    @property
    def _llm_type(self) -> str:
        return "mock_telecom_llm"

def get_llm() -> BaseChatModel:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    api_base = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    model_name = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    
    # Check if a valid API key was loaded
    has_key = bool(api_key and api_key.strip() and not api_key.startswith("your-"))
    key_prefix = api_key[:8] + "..." if (has_key and len(api_key) > 8) else "None"
    
    print(f"[LLM LOG] Config: model={model_name}, api_base={api_base}, key_present={has_key} ({key_prefix})", flush=True)
    
    if has_key:
        # Since DeepSeek is OpenAI-compatible, we can use ChatOpenAI.
        # Pass both new base_url/api_key and legacy parameters to guarantee compatibility across langchain-openai versions.
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=api_base,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.2
        )
    else:
        print("[LLM INFO] DEEPSEEK_API_KEY not set or is template. Using local MockTelecomLLM for demo.", flush=True)
        return MockTelecomLLM()

# --- LANGGRAPH NODE FUNCTIONS ---

def triage_node(state: AgentState) -> Dict[str, Any]:
    """Classifies the query and greets/responds to the user."""
    llm = get_llm()
    
    system_prompt = (
        "You are an AI customer support triage bot for a telecom company.\n"
        "Your task is to classify the customer's query into exactly one of these categories:\n"
        "- 'billing': query is about charges, billing details, payments, late fees.\n"
        "- 'technical_support': query is about slow speeds, disconnections, router lights, DSL/fiber outages.\n"
        "- 'plan_upgrade': query is about changing plans, upgrading speed, looking for cheaper options.\n"
        "- 'general': query is a greeting, appreciation, or general conversation.\n\n"
        "You must respond in exactly the following format:\n"
        "CATEGORY: <category>\n"
        "REASONING: <brief explanation>\n"
        "RESPONSE: <your helpful, warm customer response according to category>\n\n"
        "Make sure to strictly output this format."
    )
    
    # Run the model
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm.invoke(messages)
    content = response.content
    
    # Parse the category
    category_match = re.search(r"CATEGORY:\s*(\w+)", content, re.IGNORECASE)
    category = "general"
    if category_match:
        parsed_cat = category_match.group(1).lower().strip()
        if parsed_cat in ["billing", "technical_support", "plan_upgrade", "general"]:
            category = parsed_cat
            
    # Extract the response text
    response_match = re.search(r"RESPONSE:\s*(.*)", content, re.DOTALL | re.IGNORECASE)
    response_text = response_match.group(1).strip() if response_match else content
    
    # Strip categorization prefixes if LLM put them in the final response
    response_text = re.sub(r"^(CATEGORY|REASONING|RESPONSE):.*$", "", response_text, flags=re.MULTILINE).strip()
    
    logs = list(state.get("agent_logs", []))
    logs.append(f"[TRIAGE] Classified query as: {category.upper()}")
    
    return {
        "category": category,
        "messages": [AIMessage(content=response_text)],
        "agent_logs": logs
    }

def billing_handler_node(state: AgentState) -> Dict[str, Any]:
    """Handles details for billing inquiries by querying SQLite."""
    logs = list(state.get("agent_logs", []))
    logs.append("[BILLING] Querying SQLite billing records for customer...")
    customer_id = state.get("customer_id", "CUST-9948")
    
    bill = telecom_db.get_bill(customer_id)
    if bill:
        amount = bill.get("amount")
        late_fee = bill.get("late_fee", 0)
        overage = bill.get("data_overage_fee", 0)
        due = bill.get("due_date", "N/A")
        logs.append(f"[BILLING] SQL RESULT: Found bill of ${amount:.2f} due on {due} (Late Fee: ${late_fee:.2f}, Overages: ${overage:.2f}).")
    else:
        logs.append("[BILLING] SQL RESULT: No active invoices found in DB.")
        
    return {
        "agent_logs": logs
    }

def plan_upgrade_handler_node(state: AgentState) -> Dict[str, Any]:
    """Handles logic for switching plans by querying SQLite customer configuration."""
    logs = list(state.get("agent_logs", []))
    logs.append("[PLANS] Fetching customer plan parameters from SQLite...")
    customer_id = state.get("customer_id", "CUST-9948")
    
    customer = telecom_db.get_customer(customer_id)
    if customer:
        logs.append(f"[PLANS] SQL RESULT: Current subscription is {customer.get('plan_name')} ({customer.get('speed_tier')}).")
    
    logs.append("[PLANS] Fetching available telecom packages from DB...")
    logs.append("[PLANS] Available upgrades: Basic 300M ($50), Medium 500M ($65), Ultra 1G ($80).")
    
    return {
        "agent_logs": logs
    }

def generate_general_response_node(state: AgentState) -> Dict[str, Any]:
    """Generates standard chatbot replies."""
    logs = list(state.get("agent_logs", []))
    logs.append("[GENERAL] Generating standard agent response...")
    return {
        "agent_logs": logs
    }

def diagnose_router_node(state: AgentState) -> Dict[str, Any]:
    """Reads telemetry status from SQLite (which acts as the diagnostic check)."""
    logs = list(state.get("agent_logs", []))
    retry = state.get("retry_count", 0)
    customer_id = state.get("customer_id", "CUST-9948")
    
    logs.append(f"[DIAGNOSTIC] Running SQLite line diagnostics check (Attempt {retry + 1})...")
    
    # Read metrics directly from SQLite database
    telemetry = telecom_db.get_router_telemetry(customer_id)
    if not telemetry:
        # Fallback values
        telemetry = {
            "snr_db": 8.4,
            "packet_loss_pct": 14.5,
            "port_status": "degraded",
            "is_online": 1,
            "firmware_version": "v4.2.1-r3"
        }
        
    snr = telemetry.get("snr_db", 8.4)
    loss = telemetry.get("packet_loss_pct", 14.5)
    port_status = telemetry.get("port_status", "degraded")
    
    logs.append(f"[DIAGNOSTIC] SQL RESULT: Line profile is '{port_status}'. SNR: {snr} dB | Packet Loss: {loss}%.")
        
    return {
        "router_status": dict(telemetry),
        "diagnostics_run": True,
        "agent_logs": logs
    }

def apply_fix_node(state: AgentState) -> Dict[str, Any]:
    """Applies a remedy action by performing SQL database updates on telemetry metrics."""
    logs = list(state.get("agent_logs", []))
    retry = state.get("retry_count", 0)
    customer_id = state.get("customer_id", "CUST-9948")
    
    if retry == 0:
        fix_action = "router_reboot"
        logs.append("[ACTION] Sending Remote Command: REBOOT_GATEWAY. Simulating router warm reboot...")
        # Write slightly improved metrics to the SQL DB
        telecom_db.update_router_telemetry(customer_id, snr_db=10.1, packet_loss_pct=5.8, port_status="degraded")
        logs.append("[SQL UPDATE] Reboot metrics written to SQLite. SNR: 10.1 dB (Degraded).")
    elif retry == 1:
        fix_action = "port_reset"
        logs.append("[ACTION] Sending Exchange Command: PORT_RESET on physical DSLAM/fiber line switch...")
        # Write fully resolved metrics to the SQL DB
        telecom_db.update_router_telemetry(customer_id, snr_db=19.5, packet_loss_pct=0.05, port_status="normal")
        logs.append("[SQL UPDATE] Reset port metrics written to SQLite. SNR: 19.5 dB (Normal).")
    else:
        fix_action = "none"
        logs.append("[ACTION] Max autonomous remedies reached. Manual support required.")
        
    return {
        "current_fix": fix_action,
        "retry_count": retry + 1,
        "agent_logs": logs
    }

def resolve_technical_support_node(state: AgentState) -> Dict[str, Any]:
    """Formulates the final message indicating tech issue is successfully resolved."""
    logs = list(state.get("agent_logs", []))
    logs.append("[RESOLVE] Support loop finished. Connection restored successfully.")
    
    resolution_msg = (
        "Good news! Our diagnostic checks confirm your line status has returned to normal.\n\n"
        "**Modem Telemetry:**\n"
        "- **Signal strength (SNR):** 19.5 dB (Excellent)\n"
        "- **Packet loss:** 0.05% (Healthy)\n"
        "- **Status:** Normal / Active\n\n"
        "I triggered an autonomous reboot followed by a port reset on our local exchange card, which seems to have cleared the line noise. "
        "Could you please check if your browsing speed has recovered?"
    )
    
    return {
        "solution_found": True,
        "messages": [AIMessage(content=resolution_msg)],
        "agent_logs": logs
    }

def escalate_technical_support_node(state: AgentState) -> Dict[str, Any]:
    """Formulates a ticket and escalates when loops don't fix the issue."""
    logs = list(state.get("agent_logs", []))
    logs.append("[ESCALATE] Support loop finished. Fixes failed. Creating engineering ticket...")
    
    ticket_num = "TK-90812-TEL"
    escalation_msg = (
        "I have performed remote troubleshooting actions (modem reboot and exchange port reset), but the line diagnostic test "
        "is still showing degraded signal quality.\n\n"
        f"I have raised a high-priority ticket (**{ticket_num}**) for our engineering field team. "
        "An on-site line technician will run physical checks on your street cabinet within the next 4 hours. "
        "No further action is required from your end. You will receive updates via SMS. Is there any other query I can help with?"
    )
    
    return {
        "solution_found": False,
        "messages": [AIMessage(content=escalation_msg)],
        "agent_logs": logs
    }

# --- LANGGRAPH ROUTING CONDITIONAL EDGES ---

def triage_routing(state: AgentState) -> str:
    """Routes based on the triage categorization."""
    category = state.get("category", "general")
    if category == "technical_support":
        return "diagnose_router"
    elif category == "billing":
        return "billing_handler"
    elif category == "plan_upgrade":
        return "plan_upgrade_handler"
    else:
        return "generate_general_response"

def diagnostic_routing(state: AgentState) -> str:
    """Decides whether to try fixing, escalate, or finish technical support."""
    status = state.get("router_status", {})
    retry = state.get("retry_count", 0)
    
    if status.get("port_status") == "normal":
        return "resolve_technical_support"
    else:
        if retry < 2:
            return "apply_fix"
        else:
            return "escalate_technical_support"

# --- GRAPH BUILDER ---

def create_telecom_graph() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("billing_handler", billing_handler_node)
    workflow.add_node("plan_upgrade_handler", plan_upgrade_handler_node)
    workflow.add_node("generate_general_response", generate_general_response_node)
    workflow.add_node("diagnose_router", diagnose_router_node)
    workflow.add_node("apply_fix", apply_fix_node)
    workflow.add_node("resolve_technical_support", resolve_technical_support_node)
    workflow.add_node("escalate_technical_support", escalate_technical_support_node)
    
    # Set Entry Point
    workflow.set_entry_point("triage")
    
    # Add Conditional Edges from Triage
    workflow.add_conditional_edges(
        "triage",
        triage_routing,
        {
            "diagnose_router": "diagnose_router",
            "billing_handler": "billing_handler",
            "plan_upgrade_handler": "plan_upgrade_handler",
            "generate_general_response": "generate_general_response"
        }
    )
    
    # Technical Support loop with conditional checks
    workflow.add_conditional_edges(
        "diagnose_router",
        diagnostic_routing,
        {
            "resolve_technical_support": "resolve_technical_support",
            "apply_fix": "apply_fix",
            "escalate_technical_support": "escalate_technical_support"
        }
    )
    
    # Loop from applying fix back to diagnosing
    workflow.add_edge("apply_fix", "diagnose_router")
    
    # Direct terminal transitions to END
    workflow.add_edge("billing_handler", END)
    workflow.add_edge("plan_upgrade_handler", END)
    workflow.add_edge("generate_general_response", END)
    workflow.add_edge("resolve_technical_support", END)
    workflow.add_edge("escalate_technical_support", END)
    
    # Compile Graph
    return workflow.compile()

# Test runner instance helper
def run_agent_turn(messages_list: list, retry_count: int = 0) -> Dict[str, Any]:
    graph = create_telecom_graph()
    initial_state = {
        "messages": messages_list,
        "customer_id": "CUST-9948",
        "category": "general",
        "diagnostics_run": False,
        "router_status": {},
        "retry_count": retry_count,
        "current_fix": "",
        "agent_logs": ["[INIT] Session started"],
        "solution_found": False
    }
    
    result = graph.invoke(initial_state)
    return result
