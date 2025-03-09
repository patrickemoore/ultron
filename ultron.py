import openai
import os
import json
import asyncio
import tkinter as tk
import logging
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def query_assistant(prompt, depth=1):
    logging.info(f"Depth {depth}: Querying assistant with prompt:\n{prompt}")
    try:
        # Load tool definition from run_bash_script.json
        tool_path = os.path.join(os.path.dirname(__file__), "tools", "run_bash_script.json")
        with open(tool_path, "r") as f:
            tool_def = json.load(f)
        assistant = openai.beta.assistants.create(
            name="assistant",
            instructions=prompt,
            description="Recursive assistant",
            model="gpt-4o",
            tools=[tool_def]
        )
        thread_obj = openai.beta.threads.create()
        openai.beta.threads.messages.create(
            thread_id=thread_obj.id,
            role="user",
            content=prompt
        )
        run = openai.beta.threads.runs.create_and_poll(
            thread_id=thread_obj.id,
            assistant_id=assistant.id,
        )
        if run.status == 'completed':
            messages = openai.beta.threads.messages.list(thread_id=thread_obj.id)
            assistant_msg = next((msg for msg in messages if getattr(msg, "role", None) == "assistant"), None)
            if assistant_msg:
                result = str(getattr(assistant_msg, "content", ""))
                logging.info(f"Depth {depth}: Assistant response:\n{result}")
                return result
            result = "No assistant message found."
            logging.info(f"Depth {depth}: {result}")
            return result
        logging.info(f"Depth {depth}: Run status: {run.status}")
        return run.status
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logging.error(f"Depth {depth}: {error_msg}")
        return error_msg

def generate_subprocesses(overall_spec, depth=1):
    prompt_text = (
        "You are an assistant that generates a list of a few (2-4 at most) distinct subprocesses for a codebase oriented project. "
        "If subprocesses are produced, ensure that at least 2 subprocesses are output. For example, an App may consist of a frontend, backend, "
        "database, and deployment processes. Each process will have domain over a specific subdirectory and responsibilities related to the codebase. "
        "Include in the prompt for each subprocess a detailed interface it needs to implement. Given the project specification, output a JSON object "
        "following this schema: {\"processes\": [ {\"role\": <string>, \"prompt\": <string>, \"interface\": <string>} ] }"
    )
    logging.info(f"Depth {depth}: Querying for subprocesses with overall spec:\n{overall_spec}")
    try:
        response = openai.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": overall_spec}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "processes",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "processes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string"},
                                        "prompt": {"type": "string"},
                                        "interface": {"type": "string"}
                                    },
                                    "required": ["role", "prompt", "interface"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["processes"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )
        proc_data = json.loads(response.choices[0].message.content)
        logging.info(f"Depth {depth}: Received subprocesses:\n{json.dumps(proc_data, indent=2)}")
        return proc_data["processes"]
    except Exception as e:
        logging.error(f"Depth {depth}: Error generating subprocesses: {e}")
        return []

async def async_query_assistant(prompt, depth=1):
    return await asyncio.to_thread(query_assistant, prompt, depth)

async def async_generate_subprocesses(overall_spec, depth=1):
    return await asyncio.to_thread(generate_subprocesses, overall_spec, depth)

class ProcessManager:
    def __init__(self, overall_spec, depth=1):
        self.overall_spec = overall_spec
        self.depth = depth
        self.response = ""
        self.interface = {"prompt": overall_spec, "output": "", "children": {}}
    async def execute(self):
        logging.info(f"Depth {self.depth}: Executing ProcessManager with spec:\n{self.overall_spec}")
        self.response = await async_query_assistant(self.overall_spec, self.depth)
        self.interface["output"] = self.response
        if self.depth < 3:
            subprocesses = await async_generate_subprocesses(self.overall_spec, self.depth)
            if subprocesses and len(subprocesses) < 2:
                logging.warning(f"Depth {self.depth}: Only one subprocess produced, which is unhelpful. Skipping further subprocess queries.")
            else:
                tasks = []
                for proc in subprocesses:
                    child_manager = ProcessManager(proc["prompt"], depth=self.depth+1)
                    task = asyncio.create_task(child_manager.execute())
                    tasks.append((proc["role"], task))
                for role, task in tasks:
                    child_interface = await task
                    self.interface["children"][role] = child_interface
        else:
            logging.info(f"Depth {self.depth}: Maximum recursion depth reached. Not querying further subprocesses.")
        return self.interface

class ProjectTreeRenderer:
    def __init__(self, manager, width=800, height=600):
        self.manager = manager
        self.window = tk.Tk()
        self.window.title("Visual Project Tree")
        self.canvas = tk.Canvas(self.window, width=width, height=height, bg="white")
        self.canvas.pack(fill="both", expand=True)
        self.global_x = 0
        self.tooltip = None
        self.x_spacing = 100
        self.y_spacing = 100
        self.box_width = 120
        self.box_height = 60
        self.offset_x = 50
        self.offset_y = 50
        self.update_canvas()
    def create_tree_nodes(self, interface, label="Root"):
        node = {"label": label, "prompt": interface.get("prompt", ""), "output": interface.get("output", ""), "children": {}}
        for role, child_interface in interface.get("children", {}).items():
            node["children"][role] = self.create_tree_nodes(child_interface, label=role)
        return node
    def layout_tree(self, node, depth=0):
        for role, child in node["children"].items():
            self.layout_tree(child, depth+1)
        if not node["children"]:
            node["x"] = self.global_x
            self.global_x += 1
        else:
            node["x"] = sum(child["x"] for child in node["children"].values()) / len(node["children"])
        node["y"] = depth
    def draw_tree(self, node):
        x = node["x"] * self.x_spacing + self.offset_x
        y = node["y"] * self.y_spacing + self.offset_y
        left = x - self.box_width / 2
        top = y - self.box_height / 2
        right = x + self.box_width / 2
        bottom = y + self.box_height / 2
        tag = f"node_{node['x']}_{node['y']}"
        self.canvas.create_rectangle(left, top, right, bottom, fill="lightblue", tags=(tag,))
        self.canvas.create_text(x, y, text=node["label"], font=("Helvetica", 10), tags=(tag,))
        self.canvas.tag_bind(tag, "<Enter>", lambda e, p=node["prompt"]: self.show_tooltip(e, p))
        self.canvas.tag_bind(tag, "<Leave>", self.hide_tooltip)
        for role, child in node["children"].items():
            child_x = child["x"] * self.x_spacing + self.offset_x
            child_y = child["y"] * self.y_spacing + self.offset_y - self.box_height / 2
            self.canvas.create_line(x, bottom, child_x, child_y, arrow=tk.LAST)
            self.draw_tree(child)
    def update_canvas(self):
        self.canvas.delete("all")
        tree_data = self.create_tree_nodes(self.manager.interface, "Root")
        self.global_x = 0
        self.layout_tree(tree_data)
        self.draw_tree(tree_data)
        self.window.after(100, self.update_canvas)
    def show_tooltip(self, event, prompt):
        if self.tooltip:
            self.tooltip.destroy()
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 10, event.y_root + 10))
        label = tk.Label(self.tooltip, text=prompt, justify="left", background="#ffffe0", relief="solid", borderwidth=1, font=("Helvetica", 9))
        label.pack(ipadx=1)
    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
    def run(self):
        self.window.mainloop()

def run_async_manager(manager):
    asyncio.run(manager.execute())

overall_spec = input("Enter overall project specification: ")
manager = ProcessManager(overall_spec)
manager_thread = threading.Thread(target=run_async_manager, args=(manager,))
manager_thread.start()
renderer = ProjectTreeRenderer(manager)
renderer.run()
manager_thread.join()
