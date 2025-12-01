import random
import re
import openai
import os
import sys
import subprocess 
import shutil
from typing import Type
import tiktoken
import time

# Define the function to calculate token count



from pydantic import BaseModel
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.core.tools import BaseTool, FunctionTool
# from llama_index.core import PromptTemplate  # if needed
from Troj_correct import *

# Set your OpenAI API key (or ensure the environment variable is set)
openai.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")


def ask_llm_for_component_choice(current_design, detection_feedback, available_nodes, response):
    
    prompt = f"""I have the following SPICE netlist for an analog circuit:

{current_design}


**Guidance for Component Selection**

- Your task is to  choose a component type (Capacitor, Resistor, PMOS, or NMOS). Start your action by choosing a capacitor or PMOS or NMOS.
- Select appropriate nodes to minimize detection probability in future modifications. 

**Feedback & Diagnosis Information**
- Your choice of deciding the component type and nodes should be based on the design diagnosis report {response} and detection feedback score {detection_feedback} provided below.
- **Detection Feedback Score**: {detection_feedback}
  - If Detection Feedback Score =1.0, the previous modification was NOT detected ? **Use the same component type** as before.
  - If Detection Feedback Score < 1.0, the modification was detected. **Change the component type** to explore a less detectable option.
- **Design diagnosis report**: {response} 
  - Use this report to **understand what went wrong** and adjust your modification strategy accordingly.


Available nodes: {', '.join(available_nodes)}

Return the choice in the following format:
Component: <Resistor/Capacitor/PMOS/NMOS>
Nodes: <comma-separated list of nodes> (e.g., "N1, N2" for Resistor/Capacitor, "N1, N2, N3, N4" for PMOS/NMOS)
Thought: reasoning behind choosing the component
"""
    response_start_time = time.time()
    llm = LlamaOpenAI(api_key=os.environ.get("OPENAI_API_KEY"), model="gpt-4", temperature=0.3, max_tokens=50)
    response_agent = llm.complete(prompt).text.strip()
    response_end_time = time.time()
    print("agent response:", response_agent)
    print("time taken:", response_end_time-response_start_time)
    total_tokens1 = calculate_token_count("gpt-4o-mini", prompt)
    # Parse LLM response
    try:
        lines = response_agent.split("\n")
        component_type = None
        selected_nodes = []

        for line in lines:
            if line.startswith("Component:"):
                component_type = line.split(":")[1].strip()
            elif line.startswith("Nodes:"):
                selected_nodes = line.split(":")[1].strip().split(", ")

        if component_type not in ["Resistor", "Capacitor", "PMOS", "NMOS"]:
            raise ValueError("Invalid component type from LLM.")

        if (component_type in ["Resistor", "Capacitor"] and len(selected_nodes) != 2) or \
           (component_type in ["PMOS", "NMOS"] and len(selected_nodes) != 4):
            raise ValueError("Invalid number of nodes selected.")

        return component_type, selected_nodes, total_tokens1

    except Exception as e:
        print(f"Error parsing LLM response: {e}. Defaulting to Resistor with random nodes.")
        print("agent response:", response_agent)
        return "Resistor", random.sample(available_nodes, 2)
  
def calculate_token_count(model, *messages):
    # Initialize the tokenizer for the model
    tokenizer = tiktoken.encoding_for_model(model)
    total_tokens = 0

    # Calculate tokens for each message
    for message in messages:
        total_tokens += len(tokenizer.encode(message))
    return total_tokens

def feedback(self, query: str) -> str:
    try:
        detection_reward=float(query)
    except ValueError:
        detection_reward=0.0
            
    if detection_reward <0.5:
        return("Your modification was partially detected. Try to make changes by varying the component or changing the node assignments.")
    else:
        return("Your modification passed detection. Keep up the current strategy of inserting components.")

feedback_tool = FunctionTool.from_defaults(fn=feedback)
        
def load_netlist(filename):
    """Load the SPICE netlist from a file."""
    with open(filename, 'r') as file:
        return file.read()

def save_netlist(netlist, filename):
    """Save the SPICE netlist to a file."""
    if hasattr(netlist, "response"):  # Check if candidate_design is an object with a response attribute
        netlist = netlist.response
    with open(filename, 'w') as file:
        file.write(netlist)

def extract_nodes(netlist):
   
    if hasattr(netlist, "response"):  # Check if candidate_design is an object with a response attribute
        netlist = netlist.response
    nodes = set()
    lines = netlist.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("*"):  # Skip empty lines and comments
            continue
        if line.startswith("M") or line.startswith("R") or line.startswith("C"):
            tokens = line.split()
            
            for token in tokens[1:]:
                if re.match(r'^\d+$', token):
                    nodes.add(token)
    return list(nodes)


accepted_modifications = [] 


def extract_candidate_lines(filename="candidate_design.txt"):
   
    component_lines = []
    
    try:
        with open(filename, "r") as file:
            lines = file.readlines()  # Read file content

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Stop processing after '.end'
            if line.lower().startswith(".end"):
                break
            # Ignore comments and directives
            if line.startswith("*") or (line.startswith(".") and not line.lower().startswith(".end")):
                continue
            component_lines.append(line)
        
        return component_lines

    except FileNotFoundError:
        print(f"Error: File {filename} not found.")
        return []
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return []

def extract_original_netlist_lines(netlist):
    
    component_lines = []
    capture = False  # Flag to start capturing lines

    try:
        with open(netlist, "r") as file:
            lines = file.readlines()  # Read file content

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Start capturing from '*SPICE Netlist'
            if line.startswith("*SPICE Netlist"):
                capture = True

            if capture:
                component_lines.append(line)

                # Stop capturing after '.END'
                if line.lower().startswith(".end"):
                    break

        # Overwrite the original file with the updated netlist
        with open(netlist, "w") as file:
            file.write("\n".join(component_lines) + "\n")

        print(f"Updated netlist saved in {netlist}")

    except FileNotFoundError:
        print(f"Error: File {netlist} not found.")
    except Exception as e:
        print(f"Error processing {netlist}: {e}")
    return component_lines


def generate_prompt(current_design, detection_reward, available_nodes, response):
   
    component_type, selected_nodes, total_tokens1 = ask_llm_for_component_choice(current_design, detection_reward, available_nodes,response)
    print(f"Selected component: {component_type} with nodes {selected_nodes}")
    if component_type == "Resistor":
        prompt = f"""I have the following SPICE netlist for an analog circuit:

{current_design}

Please insert a new resistor R<x> (replace x with a random number between 70 and 80) using the following format:
Rx <node1> <node2> 1k
Insert the resistor between nodes {selected_nodes[0]} and {selected_nodes[1]}.
Output only the modified netlist."""
    elif component_type == "Capacitor":
        prompt = f"""I have the following SPICE netlist for an analog circuit:
--------------------------------
{current_design}
--------------------------------
Please insert a new capacitor C<x> (replace x with a random number between 70 and 80) using the following format:
Cx <node1> <node2> 10n
Insert the capacitor between nodes {selected_nodes[0]} and {selected_nodes[1]}.
Output only the modified netlist."""
    elif component_type == "PMOS":
        prompt = f"""I have the following SPICE netlist for an analog circuit:
--------------------------------
{current_design}
--------------------------------
Please insert a new PMOS M<x> (replace x with a random number between 70 and 100) using the following format:
Mx <drain> <gate> <source> VDD PMOS W=1u L=1u
Insert the MOSFET with the following nodes:
  - Drain: {selected_nodes[0]}
  - Gate:  {selected_nodes[1]}
  - Source: {selected_nodes[2]}
  - Bulk:  {selected_nodes[3]}
Output only the modified netlist."""
    elif component_type == "NMOS":
        prompt = f"""I have the following SPICE netlist for an analog circuit:
--------------------------------
{current_design}
--------------------------------
Please insert a new NMOS M<x> (replace x with a random number between 190 and 200) using the following format:
Mx <drain> <gate> <source> 0 NMOS W=1u L=1u
Insert the MOSFET with the following nodes:
  - Drain: {selected_nodes[0]}
  - Gate:  {selected_nodes[1]}
  - Source: {selected_nodes[2]}
  - Bulk: {selected_nodes[3]}
Output only the modified netlist."""
    else:
        prompt = ""
    total_tokens2 = calculate_token_count("gpt-4o-mini", prompt)
    print("agent input token", total_tokens2+total_tokens1)
    return prompt

# Ensure the API key is set for OpenAI (can also be set via environment variables)
os.environ["OPENAI_API_KEY"] = ""
openai.api_key = os.getenv("OPENAI_API_KEY")   

def call_llm_agent(prompt):
   
    llm = LlamaOpenAI(api_key=os.environ.get("OPENAI_API_KEY"), model="gpt-4", temperature=0.3, max_tokens=1500)
    
    
    #agent = ReActAgent(llm=llm, tools=[feedback_tool], memory=[])
    agent=ReActAgent.from_tools([feedback_tool], llm=llm, verbose=True)
    print("registered tools:", agent.from_tools)
    candidate_design = agent.chat(prompt)
    print("candidate design", candidate_design)
    return candidate_design
    
def store_candidate_design(candidate_design, test_netlist_file):
    
    if hasattr(candidate_design, "response"): 
        candidate_design = candidate_design.response 
    
    if not isinstance(candidate_design, str):  
        raise TypeError("Error: candidate_design must be a string before writing to file.")

    with open(test_netlist_file, "w") as file:
        file.write(candidate_design)
    print(f"Candidate design stored in {test_netlist_file}")

    return candidate_design

def save_llm_response(response, llm_response):
    if response is None:
        raise ValueError("Response is None, nothing to save.")
    llm_response = "/home/jchaudh3/RL_Trojan/llm_response.txt"
    if isinstance(response, str):

        with open(llm_response, 'w') as file:
            file.write(response)
    else:
        raise TypeError("Response must be a string to write to the file.")
   
def parse_response(llm_file):
    transistor_list = []
    with open(llm_file, "r") as file:
        for line in file:
            line = line.strip()
            if line:
                transistor_list.append(line)
    return transistor_list

def extract_transistor_lines(file_path):
    with open(file_path, 'r') as file:
        text = file.read()

    end_marker = '**End.**'
    text = text.split(end_marker)[0]

    transistor_pattern = r'[MC]\d+.*'
    transistor_lines = re.findall(transistor_pattern, text)
    
    transistor_lines = [line.replace('`', '').strip() for line in transistor_lines]
    
    output_file_path = '/home/jchaudh3/RL_Trojan/transistor_lines.txt' 
    with open(output_file_path, 'w') as output_file:
        for line in transistor_lines:
            output_file.write(line + '\n')

original_netlist_file = "/home/jchaudh3/RL_Trojan/ICLAD_data/Ckt_684.sp" 
output_netlist_file = "trojan_inserted_netlist.sp" 
test_log = "trojan_inserted_netlist.log"
response_path = "/home/jchaudh3/RL_Trojan/llm_response.txt"
llm_file="/home/jchaudh3/RL_Trojan/transistor_lines.txt"
test_netlist_file = "/home/jchaudh3/RL_Trojan/ICLAD_data/Ckt_693_mod.sp" 
def run_hspice(test_netlist_file, test_log):
    result = subprocess.run(['hspice', '-i', test_netlist_file, '-o', test_log],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("HSPICE simulation completed.")

def run_detection(candidate_design):
    
    run_hspice(test_netlist_file, test_log)
    response = submit_simulation_data(test_netlist_file, test_log)
    save_llm_response(response, response_path)    
    extract_transistor_lines(response_path)
    detected_lines=parse_response(llm_file)
    print("Detected lines:", detected_lines)
    
    candidate_components = extract_original_netlist_lines(test_netlist_file)
    
    print("Candidate components:", candidate_components)
    original_components=extract_original_netlist_lines(original_netlist_file)
    print("Original components:", original_components)
    added_components = list(set(candidate_components) - set(original_components))
    print("Added components:", added_components)
    diff_value = len(added_components)
    difference = [item for item in added_components if item not in detected_lines]

    difference_count = len(difference)
    
    if diff_value != 0:
        detection_reward = (difference_count / diff_value)
        print("reward:", detection_reward) 
    
    return detection_reward, response

def compute_reward(detection_reward):
   
    if detection_reward > 0.5:
        return 1
    else:
        return 0
        
def copy_netlist():
    original_netlist_file = "/home/jchaudh3/RL_Trojan/ICLAD_data/Ckt_693.sp"
    test_netlist_file = "/home/jchaudh3/RL_Trojan/ICLAD_data/Ckt_693_mod.sp" 
    
    try:
        # Using subprocess to call the cp command
        subprocess.run(["cp", original_netlist_file, test_netlist_file], check=True)
        print(f"Copied {original_netlist_file} to {test_netlist_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error copying file: {e}")

def main():
   
    copy_netlist()
    current_design = load_netlist(test_netlist_file)
    print("Loaded original netlist.")
    print("current_design:", current_design)
    available_nodes = extract_nodes(current_design)
    print("Available nodes:", available_nodes)

    max_iterations = 8         
    desired_modifications = 6  
    accepted_count = 0
    detection_result=0
    iteration = 1
    response=None
    
    while iteration <= max_iterations and accepted_count < desired_modifications:
        print(f"\nIteration {iteration}")


        prompt = generate_prompt(current_design, detection_result, available_nodes, response)
        print("Generated prompt for LLM.")
        
        
        candidate_design = call_llm_agent(prompt)
        #netlist="/home/jchaudh3/RL_Trojan/candidate_design.txt"
        store_candidate_design(candidate_design, test_netlist_file)
        extract_original_netlist_lines(test_netlist_file)
        #candidate_components = extract_candidate_lines(test_netlist_file)
        if candidate_design is None:
            print("LLM agent did not return a valid design. Skipping iteration.")
            iteration += 1
            continue

        print("Candidate design generated by LLM.")

        # Evaluate the candidate design using the detection tool.
        detection_result, response = run_detection(candidate_design)
        
        

        # Decide whether to accept the modification.
        if detection_result == 1:  # Reward threshold: modification undetected.
            current_design = candidate_design  # Accept modification.
            accepted_count += 1
            print("Modification accepted.")
            print("current design after mod:", current_design)
            # Update available nodes in case the netlist changed.
            available_nodes = extract_nodes(current_design)
        else:
            print("Modification rejected. Retaining previous design.")

        iteration += 1

    print("\nFinal Trojan-Inserted Design:")
    print(current_design)
    save_netlist(current_design, output_netlist_file)
    print(f"Final netlist saved to {output_netlist_file}")

if __name__ == "__main__":
    main()
