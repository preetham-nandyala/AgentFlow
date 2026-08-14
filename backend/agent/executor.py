import inspect
from sqlalchemy.orm import Session as DBSession
from agent.registry import registry
from agent.session import SessionManager
from models.schema import Session

def execute_plan(db: DBSession, session_manager: SessionManager, plan: list[dict]) -> str:
    """
    Executes the generated plan step by step with output chaining.
    Each tool receives the output of the previous tool via context['previous_output'].
    """
    session_obj = session_manager.get_or_create_session(db)
    
    # Store the generated plan in execution history
    exec_history = list(session_obj.execution_history)
    exec_history.append({"plan": plan})
    session_obj.execution_history = exec_history
    db.commit()

    final_response = "Finished execution."
    outputs = []
    previous_output = None  # Chain outputs between steps

    for step in plan:
        tool_name = step.get("tool")
        args = step.get("args", {})
        
        tool = registry.get_tool(tool_name)
        if not tool:
            output = f"Tool '{tool_name}' not found."
            outputs.append({tool_name: output})
            final_response = output
            continue

        try:
            print(f"⚙️ Executing {tool_name} with args {args}")
            
            # Use inspect.signature for robust parameter detection
            sig = inspect.signature(tool.func)
            if "context" in sig.parameters:
                args["context"] = {
                    "db": db,
                    "session_manager": session_manager,
                    "session_obj": session_obj,
                    "tool_outputs": outputs,
                    "previous_output": previous_output,
                }
                
            result = tool.func(**args)
            outputs.append({tool_name: result})
            previous_output = result  # Pass this to the next step
            final_response = result
            
            
        except Exception as e:
            output = f"Error executing {tool_name}: {str(e)}"
            print(f"❌ {output}")
            outputs.append({tool_name: output})
            final_response = output
            break

    # Save outputs to session
    saved_outputs = list(session_obj.tool_outputs)
    saved_outputs.extend(outputs)
    session_obj.tool_outputs = saved_outputs
    db.commit()

    return final_response
