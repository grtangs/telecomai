import os
import gradio as gr
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# Import LangGraph telecom agent logic and database module
from telecom_agent import create_telecom_graph, AgentState
import database

# Initialize the SQLite database on startup
database.init_db()

load_dotenv()

# Pre-compile the LangGraph graph
agent_graph = create_telecom_graph()

MOCK_CUSTOMER_ID = "CUST-9948"

def generate_customer_html(customer_id: str = MOCK_CUSTOMER_ID) -> str:
    """Generates the customer profile HTML dynamically from SQLite."""
    cust = database.get_customer(customer_id)
    bill = database.get_bill(customer_id)
    
    if not cust:
        return "<div style='color: red; padding: 20px;'>Customer Profile Not Found in SQLite</div>"
        
    name = cust.get("name", "N/A")
    plan = cust.get("plan_name", "N/A")
    speed = cust.get("speed_tier", "N/A")
    ip = cust.get("ip_address", "N/A")
    status = cust.get("status", "N/A")
    
    amount = f"${bill.get('amount'):.2f}" if bill else "$0.00"
    due = bill.get("due_date", "N/A") if bill else "N/A"
    
    # Apply dynamic colors for statuses
    if "Optimal" in status or "Normal" in status:
        status_color = "#38A169"  # Green
    elif "Degraded" in status:
        status_color = "#DD6B20"  # Orange
    else:
        status_color = "#E53E3E"  # Red
        
    return f"""
    <div style="background-color: #0f172a; border-radius: 12px; padding: 20px; border: 1px solid #1e293b; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
        <h3 style="margin: 0 0 15px 0; color: #f8fafc; font-size: 16px; font-family: 'Outfit', sans-serif; border-bottom: 1px solid #1e293b; padding-bottom: 10px;">👤 CUSTOMER PROFILE (SQLITE)</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px; color: #cbd5e1;">
            <tr style="height: 30px;"><td style="color: #64748b;">Customer Name</td><td><strong>{name}</strong></td></tr>
            <tr style="height: 30px;"><td style="color: #64748b;">Account ID</td><td><code>{customer_id}</code></td></tr>
            <tr style="height: 30px;"><td style="color: #64748b;">Subscription</td><td><strong>{plan} ({speed})</strong></td></tr>
            <tr style="height: 30px;"><td style="color: #64748b;">IP / Device</td><td><code>{ip}</code></td></tr>
            <tr style="height: 30px;"><td style="color: #64748b;">System Status</td><td style="color: {status_color}; font-weight: bold;">{status}</td></tr>
            <tr style="height: 30px;"><td style="color: #64748b;">Account Balance</td><td style="color: #f43f5e; font-weight: bold;">{amount}</td></tr>
            <tr style="height: 30px;"><td style="color: #64748b;">Payment Due</td><td>{due}</td></tr>
        </table>
    </div>
    """

def generate_telemetry_html(router_status: dict) -> str:
    """Generates a premium looking status card for the modem telemetry."""
    if not router_status:
        # Default state before any troubleshooting
        snr = 8.4
        loss = 14.5
        port_status = "degraded"
        status_label = "Degraded Telemetry"
        border_color = "#E53E3E"  # Red
        status_color = "#FED7D7"
        bg_status = "#9B2C2C"
    else:
        snr = router_status.get("snr_db", 8.4)
        loss = router_status.get("packet_loss_pct", 14.5)
        port_status = router_status.get("port_status", "degraded")
        
        if port_status == "normal":
            status_label = "Normal (Optimal)"
            border_color = "#38A169"  # Green
            status_color = "#C6F6D5"
            bg_status = "#22543D"
        else:
            status_label = "Degraded Telemetry"
            border_color = "#DD6B20"  # Orange
            status_color = "#FEEBC8"
            bg_status = "#7B341E"

    return f"""
    <div style="background: linear-gradient(135deg, #1e293b, #0f172a); border-radius: 12px; padding: 20px; border: 1px solid #334155; border-left: 6px solid {border_color}; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
        <h3 style="margin: 0 0 15px 0; color: #f8fafc; font-size: 16px; font-family: 'Outfit', sans-serif; display: flex; justify-content: space-between; align-items: center;">
            <span>📡 MODEM DIAGNOSTIC TELEMETRY</span>
            <span style="background-color: {bg_status}; color: {status_color}; font-size: 11px; padding: 3px 8px; border-radius: 12px; font-weight: 600;">{status_label}</span>
        </h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-family: monospace; font-size: 13px;">
            <div style="background-color: #1e293b; padding: 8px; border-radius: 6px; border: 1px solid #334155;">
                <span style="color: #94a3b8; display: block; font-size: 11px; margin-bottom: 2px;">SIGNAL-TO-NOISE RATIO</span>
                <strong style="color: {'#38a169' if snr >= 15 else '#e53e3e'}; font-size: 14px;">{snr} dB</strong>
            </div>
            <div style="background-color: #1e293b; padding: 8px; border-radius: 6px; border: 1px solid #334155;">
                <span style="color: #94a3b8; display: block; font-size: 11px; margin-bottom: 2px;">PACKET LOSS RATIO</span>
                <strong style="color: {'#38a169' if loss <= 1 else '#e53e3e'}; font-size: 14px;">{loss}%</strong>
            </div>
            <div style="background-color: #1e293b; padding: 8px; border-radius: 6px; border: 1px solid #334155;">
                <span style="color: #94a3b8; display: block; font-size: 11px; margin-bottom: 2px;">EXCHANGE PORT PROFILE</span>
                <strong style="color: {'#38a169' if port_status == 'normal' else '#e53e3e'}; text-transform: uppercase;">{port_status}</strong>
            </div>
            <div style="background-color: #1e293b; padding: 8px; border-radius: 6px; border: 1px solid #334155;">
                <span style="color: #94a3b8; display: block; font-size: 11px; margin-bottom: 2px;">FIRMWARE STATUS</span>
                <strong style="color: #f8fafc;">v4.2.1-r3 (Current)</strong>
            </div>
        </div>
    </div>
    """

def generate_logs_html(logs: list) -> str:
    """Generates a neat scrollable visual terminal representing LangGraph execution steps."""
    log_items = []
    for log in logs:
        # Style different levels of logs
        if "[TRIAGE]" in log:
            color = "#60a5fa"  # Blue
        elif "[DIAGNOSTIC]" in log:
            color = "#fbbf24"  # Amber
        elif "[ACTION]" in log:
            color = "#f43f5e"  # Rose
        elif "[RESOLVE]" in log:
            color = "#34d399"  # Emerald
        elif "[ESCALATE]" in log:
            color = "#a78bfa"  # Purple
        elif "[SQL UPDATE]" in log:
            color = "#f472b6"  # Pink
        else:
            color = "#94a3b8"  # Slate
            
        log_items.append(f"<div style='margin-bottom: 6px; border-bottom: 1px solid #1e293b; padding-bottom: 4px; color: {color}; font-family: monospace; font-size: 12px;'>> {log}</div>")
        
    log_content = "".join(log_items)
    return f"""
    <div style="background-color: #0b0f19; border-radius: 12px; padding: 15px; border: 1px solid #1e293b; max-height: 250px; overflow-y: auto; box-shadow: inset 0 2px 4px 0 rgba(0,0,0,0.6);">
        <h4 style="margin: 0 0 10px 0; color: #64748b; font-size: 12px; letter-spacing: 1px; font-family: sans-serif;">🤖 LANGRAPH EXECUTION STATE LOGS</h4>
        <div style="display: flex; flex-direction: column;">
            {log_content}
        </div>
    </div>
    """

# Initial Gradio state
INITIAL_STATE = {
    "messages": [],
    "retry_count": 0,
    "router_status": {},
    "agent_logs": ["[INIT] Session started. Waiting for customer query..."],
    "category": "general",
    "solution_found": False
}

def chatbot_respond(user_message: str, history: list, state: dict):
    if not user_message.strip():
        return "", history, state, generate_telemetry_html(state["router_status"]), generate_logs_html(state["agent_logs"]), generate_customer_html()
        
    # Append the new user message to the state's message list
    langchain_messages = []
    is_dict_format = False
    
    for turn in history:
        if isinstance(turn, dict):
            is_dict_format = True
            role = turn.get("role")
            content = turn.get("content")
            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            else:
                langchain_messages.append(AIMessage(content=content))
        elif isinstance(turn, (list, tuple)) and len(turn) == 2:
            langchain_messages.append(HumanMessage(content=turn[0]))
            langchain_messages.append(AIMessage(content=turn[1]))
    
    # Add latest query
    langchain_messages.append(HumanMessage(content=user_message))
    
    # Compile graph input state
    graph_input = {
        "messages": langchain_messages,
        "customer_id": MOCK_CUSTOMER_ID,
        "category": state.get("category", "general"),
        "diagnostics_run": bool(state.get("router_status")),
        "router_status": state.get("router_status", {}),
        "retry_count": state.get("retry_count", 0),
        "current_fix": state.get("current_fix", ""),
        "agent_logs": state.get("agent_logs", ["[INIT] Session started"]),
        "solution_found": state.get("solution_found", False)
    }
    
    # Execute LangGraph run
    try:
        updated_state = agent_graph.invoke(graph_input)
    except Exception as e:
        # Log error details and print full traceback to Cloud Run container logs
        import traceback
        print(f"[CRITICAL ERROR] LangGraph invoke failed: {str(e)}", flush=True)
        traceback.print_exc()
        error_logs = state.get("agent_logs", []) + [f"[ERROR] LangGraph failed: {str(e)}"]
        fallback_msg = "I encountered an issue querying the model. Please check if your DEEPSEEK_API_KEY is correct."
        if is_dict_format or len(history) == 0:
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": fallback_msg})
        else:
            history.append([user_message, fallback_msg])
        return "", history, state, generate_telemetry_html(state["router_status"]), generate_logs_html(error_logs), generate_customer_html()
    
    # Get response
    ai_response = updated_state["messages"][-1].content
    if is_dict_format or len(history) == 0:
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": ai_response})
    else:
        history.append([user_message, ai_response])
    
    # Update persistent state
    new_state = {
        "messages": [],  # Reset messages in state cache since they are fully captured in Gradio history
        "retry_count": updated_state.get("retry_count", 0),
        "router_status": updated_state.get("router_status", {}),
        "agent_logs": updated_state.get("agent_logs", []),
        "category": updated_state.get("category", "general"),
        "solution_found": updated_state.get("solution_found", False)
    }
    
    # Format updated HTML fragments
    telemetry_html = generate_telemetry_html(new_state["router_status"])
    logs_html = generate_logs_html(new_state["agent_logs"])
    customer_html = generate_customer_html()
    
    return "", history, new_state, telemetry_html, logs_html, customer_html

def clear_session():
    # Reset SQLite database records back to defaults
    database.reset_db()
    
    # Get telemetry default status (representing initial degraded state in DB)
    default_telemetry = database.get_router_telemetry(MOCK_CUSTOMER_ID)
    
    return [], INITIAL_STATE.copy(), generate_telemetry_html(default_telemetry), generate_logs_html(INITIAL_STATE["agent_logs"]), generate_customer_html()

def set_quick_suggest(query: str):
    # Returns the query to load in the input textbox
    return query

# Premium Dark CSS Customizations
custom_css = """
body {
    background-color: #0b0f19 !important;
    color: #f8fafc !important;
}
.gradio-container {
    background-color: #0b0f19 !important;
    border: none !important;
}
.sidebar-panel {
    background-color: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px;
}
.suggest-btn {
    text-align: left !important;
    font-size: 13px !important;
    padding: 8px 12px !important;
    border-radius: 8px !important;
    background-color: #1e293b !important;
    color: #f8fafc !important;
    border: 1px solid #334155 !important;
    transition: all 0.2s ease-in-out !important;
}
.suggest-btn:hover {
    background-color: #2563eb !important;
    border-color: #3b82f6 !important;
}
"""

with gr.Blocks(css=custom_css, title="Telecom Autonomic Agent Dashboard") as demo:
    # State tracker
    state_store = gr.State(value=INITIAL_STATE.copy())
    
    # Title Header
    gr.HTML(
        """
        <div style="text-align: center; margin-bottom: 25px; padding: 20px; background: linear-gradient(90deg, #1e3a8a, #0d9488); border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
            <h1 style="color: #f8fafc; margin: 0; font-family: 'Outfit', sans-serif; font-size: 28px; font-weight: 700; letter-spacing: 0.5px;">📡 Autonomic Customer Service & Diagnostics</h1>
            <p style="color: #cbd5e1; margin: 5px 0 0 0; font-size: 14px;">Powered by LangGraph Agentic Loops, SQLite Database & DeepSeek AI</p>
        </div>
        """
    )
    
    with gr.Row():
        # LEFT COLUMN - Dashboard & Logs
        with gr.Column(scale=1):
            # Customer Info Card (Dynamic SQLite widget)
            customer_widget = gr.HTML(value=generate_customer_html())
            
            gr.HTML("<div style='height: 10px;'></div>")
            
            # Live Modem Diagnostics Panel
            # Read initial state from DB
            initial_telemetry = database.get_router_telemetry(MOCK_CUSTOMER_ID)
            telemetry_widget = gr.HTML(value=generate_telemetry_html(initial_telemetry))
            
            gr.HTML("<div style='height: 10px;'></div>")
            
            # Execution state logs widget
            logs_widget = gr.HTML(value=generate_logs_html(INITIAL_STATE["agent_logs"]))
            
        # RIGHT COLUMN - Chat Interface
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="Support Assistant Chat",
                height=450
            )
            
            with gr.Row():
                user_input = gr.Textbox(
                    placeholder="Describe your issue here...",
                    show_label=False,
                    scale=4,
                    container=False
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1)
                
            with gr.Row():
                clear_btn = gr.Button("Reset Simulation", variant="stop")
                
            gr.HTML("<div style='height: 10px;'></div>")
            
            # Quick suggestions
            gr.HTML("<h4 style='color: #64748b; margin: 10px 0; font-size: 13px;'>QUICK SIMULATION PRESETS:</h4>")
            with gr.Row():
                suggest_tech = gr.Button("📶 Slow Internet Troubleshooting (Loops)", elem_classes=["suggest-btn"])
                suggest_bill = gr.Button("💵 Why is my bill so high?", elem_classes=["suggest-btn"])
                suggest_plan = gr.Button("⚡ Switch Plan / Upgrade Tier", elem_classes=["suggest-btn"])

    # Event handlers configuration
    user_input.submit(
        chatbot_respond,
        inputs=[user_input, chatbot, state_store],
        outputs=[user_input, chatbot, state_store, telemetry_widget, logs_widget, customer_widget]
    )
    submit_btn.click(
        chatbot_respond,
        inputs=[user_input, chatbot, state_store],
        outputs=[user_input, chatbot, state_store, telemetry_widget, logs_widget, customer_widget]
    )
    
    # Preset triggers
    suggest_tech.click(
        set_quick_suggest,
        inputs=[gr.State("My broadband speed has been extremely slow all day")],
        outputs=[user_input]
    )
    suggest_bill.click(
        set_quick_suggest,
        inputs=[gr.State("Why is my monthly bill $124.50? I need to review charges")],
        outputs=[user_input]
    )
    suggest_plan.click(
        set_quick_suggest,
        inputs=[gr.State("I would like to upgrade my speed tier or see what plans are available")],
        outputs=[user_input]
    )
    
    # Clear session logic (Includes database re-seeding)
    clear_btn.click(
        clear_session,
        outputs=[chatbot, state_store, telemetry_widget, logs_widget, customer_widget]
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting server on http://{host}:{port}")
    demo.launch(server_name=host, server_port=port, share=False)
