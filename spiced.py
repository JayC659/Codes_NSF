import os


class Conversation:
    def __init__(self, log_file=None):
        self.messages = []
        self.log_file = log_file

        if self.log_file and os.path.exists(self.log_file):
            open(self.log_file, 'w').close()

    def add_message(self, role, content):
        """Add a new message to the conversation."""
        self.messages.append({'role': role, 'content': content})

        if self.log_file:
            with open(self.log_file, 'a') as file:
                file.write(f"{role}: {content}\n")

    def get_messages(self):
        """Retrieve the entire conversation."""
        return self.messages

    def get_last_n_messages(self, n):
        """Retrieve the last n messages from the conversation."""
        return self.messages[-n:]

    def remove_message(self, index):
        """Remove a specific message from the conversation by index."""
        if index < len(self.messages):
            del self.messages[index]

    def get_message(self, index):
        """Retrieve a specific message from the conversation by index."""
        return self.messages[index] if index < len(self.messages) else None

    def clear_messages(self):
        """Clear all messages from the conversation."""
        self.messages = []

    def __str__(self):
        """Return the conversation in a string format."""
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.messages])
os.environ["OPENAI_API_KEY"] = ""
import openai
from abc import ABC, abstractmethod

#from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch

class AbstractLLM(ABC):
    """Abstract Large Language Model."""

    def __init__(self):
        pass

    @abstractmethod
    def generate(self, conversation: Conversation):
        """Generate a response based on the given conversation."""
        pass

class ChatGPT3p5(AbstractLLM):
    """ChatGPT Large Language Model."""

    def __init__(self):
        super().__init__()
        openai.api_key=os.environ['OPENAI_API_KEY']

    def generate(self, conversation: Conversation):
        messages = [{'role' : msg['role'], 'content' : msg['content']} for msg in conversation.get_messages()]

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages = messages,
        )

        return response.choices[0].message.content

import sys

# Allows us to log the output of the model to a file if logging is enabled
class LogStdoutToFile:
    def __init__(self, filename):
        self._filename = filename
        self._original_stdout = sys.stdout

    def __enter__(self):
        if self._filename:
            sys.stdout = open(self._filename, 'w')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._filename:
            sys.stdout.close()
        sys.stdout = self._original_stdout

def generate_verilog(conv, model_type, model_id=""):
    if model_type == "ChatGPT4":
        model = ChatGPT4()
    elif model_type == "Claude":
        model = Claude()
    elif model_type == "ChatGPT3p5":
        model = ChatGPT3p5()
    elif model_type == "PaLM":
        model = PaLM()
    elif model_type == "CodeLLama":
        model = CodeLlama(model_id)

    return(model.generate(conv))

conv = Conversation(log_file=None)

conv.add_message("system", "You are an advanced language model trained to analyze SPICE netlists and identify anomalies that could indicate the presence of hardware Trojans. You will be provided with simulation logs of MOSFET behavior and desired specifications of the output node voltage behavior. You will check if there are normal behavior patterns of MOSFETs in the simulation log and use this knowledge to check if there is a Trojan circuit in the netlist. Using the obtained knowledge, determine the nodes where the Trojan is inserted in the netlist.")


rules="""
You will follow a set of steps to identify the Trojan-impacted nodes of a circuit. The steps are as follows:

Steps for Voltage Simulation Log:

1. Analyze the voltage behavior of the output node "out" across all the input voltages.
2. Check the voltage at the output node "out" and compare against the desired specification, for all the input voltages in "vin" node.
3. If the output voltage is within the desired specification for some input voltages, list all the corresponding input voltages where the output voltage is within the desired specification.
4. From the list of input voltages where the output voltage is within the desired specification, create a list of these input voltages. Label these as 'Normal Inputs'
5. Identify and list the input voltages where the output voltage falls outside the desired specification. Label these input voltages as 'Trojan-Activation Inputs'.
6. For the 'Trojan-Activation Inputs', analyze the voltage behavior of all nodes in the circuit. Compare these node voltages to the node voltages corresponding to 'Normal Inputs'.
7. From the above step, identify any nodes where there is a significant deviation in voltage between the 'Trojan-Activation Inputs' and the 'Normal Inputs'. List these nodes where the deviation is significant.
8. For each input voltage in 'Trojan-Activation Inputs', evaluate the voltage deviations across all nodes. Determine which node exhibits the highest deviation compared to the other nodes for each of these input voltages. List the nodes with the most significant deviations.
9. Combine the lists of nodes identified in steps 7 and 8. Create a final list of nodes that include those with significant voltage deviations from 'Trojan-Activation Inputs' and those with the highest deviations across all nodes. Provide this combined list "Suspect V" as the final set of nodes of interest.

Steps for Current Simulation Log:

1. You have the set of 'Trojan-Activation Inputs' and 'Normal Inputs' identified in the previous step.
2. Using Kirchhoff's Current Law, compare the current values of all MOSFETs in the simulation log for 'Trojan-Activation Inputs' and 'Normal Inputs'. Identify and list any MOSFETs that exhibit a significant increase in current when 'Trojan-Activation Inputs' are applied compared to 'Normal Inputs'.
3. For the MOSFETs obtained above, list their corresponding nodes in the netlist. Name this list as 'Suspect I'.

Finally, print the lists "Suspect V" and "Suspect I" as the final output.


"""

conv.add_message("system", rules)
# First example
paragraph_example_1 = """Netlist 1:
* Example Netlist 1 Data *

.param VD = 5
.param dc_step = 'VD/50'
.param Vin = 5
Cunit 4 0 50pF
Cmain y 0 90pF
M80 4 3 VDD VDD PMOS W=0.5u L=0.1u
M81 4 3 y 0 NMOS W=0.5u L=0.1u
R1 37 1 1k
R2 38 2 1k
I1 3 0 DC 1mA
M2 39 34 0 0 NMOS W=1u L=1u
M6 41 34 0 0 NMOS W=1u L=1u
R4 6 1 1k
M4 4 1 3 3 NMOS W=1u L=1u
M3 5 2 3 3 NMOS W=1u L=1u
R3 2 out 1k
M82 y 0 0 0 NMOS W=0.1u L=0.1u
M8 4 20 VDD VDD PMOS W=1u L=1u
M83 1 y VDD VDD PMOS W=0.1u L=0.1u
M84 1 y 0 0 NMOS W=0.1u L=0.1u
M9 out 35 5 5 PMOS W=1u L=1u
M7 6 35 4 4 PMOS W=1u L=1u
M5 out 36 41 41 NMOS W=1u L=1u
M1 6 36 39 39 NMOS W=1u L=1u
M10 5 20 VDD VDD PMOS W=1u L=1u
V2 37 0 Vin

Voltage and Current Simulation Log 1:

* Example Voltage Simulation Log 1 Data *

vin          voltage    voltage
             6         out
    0.          2.0818   333.7313m
  100.00000m    2.1550   343.6864m
  200.00000m    2.2270   353.4371m
  300.00000m    2.2977   362.9850m
  400.00000m    2.3673   372.3314m
  500.00000m    2.4358   381.4774m
  600.00000m    2.5032   390.4236m
  700.00000m    2.5696   399.1707m
  800.00000m    2.6351   407.7189m
  900.00000m    2.6996   416.0683m
    1.00000     2.7632   424.2188m
    1.10000     2.8260   432.1702m
    1.20000     2.8879   439.9219m
    1.30000     2.9491   447.4732m
    1.40000     3.0095   454.8233m
    1.50000     3.0692   461.9711m
    1.60000     3.1281   468.9154m
    1.70000     3.1864   475.6548m
    1.80000     3.2440   482.1878m
    1.90000     3.3010   488.5127m
    2.00000     3.3574   494.6274m

 vin          voltage    voltage    voltage    voltage
             4          y          5          2
    0.          4.7337     1.1775     3.3883   166.8657m
  100.00000m    4.7313     1.1769     3.4156   171.8432m
  200.00000m    4.7289     1.1763     3.4419   176.7186m
  300.00000m    4.7267     1.1758     3.4672   181.4925m
  400.00000m    4.7245     1.1753     3.4917   186.1657m
  500.00000m    4.7225     1.1747     3.5153   190.7387m
  600.00000m    4.7205     1.1743     3.5382   195.2118m
  700.00000m    4.7187     1.1738     3.5602   199.5853m
  800.00000m    4.7170     1.1734     3.5815   203.8594m
  900.00000m    4.7153     1.1730     3.6021   208.0341m
    1.00000     4.7137     1.1726     3.6220   212.1094m
    1.10000     4.7123     1.1722     3.6412   216.0851m
    1.20000     4.7109     1.1719     3.6597   219.9609m
    1.30000     4.7096     1.1715     3.6776   223.7366m
    1.40000     4.7083     1.1712     3.6949   227.4116m
    1.50000     4.7072     1.1709     3.7115   230.9855m
    1.60000     4.7061     1.1707     3.7276   234.4577m
    1.70000     4.7052     1.1704     3.7430   237.8274m
    1.80000     4.7043     1.1702     3.7578   241.0939m
    1.90000     4.7035     1.1700     3.7721   244.2563m
    2.00000     4.7027     1.1698     3.7858   247.3137m


 vin          voltage    voltage    voltage    voltage
             37         1          38         39
    0.          0.         1.6064     0.       445.5438m
  100.00000m  100.0000m    1.6861     0.       445.9180m
  200.00000m  200.0000m    1.7649     0.       446.2852m
  300.00000m  300.0000m    1.8428     0.       446.6459m
  400.00000m  400.0000m    1.9199     0.       447.0003m
  500.00000m  500.0000m    1.9962     0.       447.3486m
  600.00000m  600.0000m    2.0718     0.       447.6913m
  700.00000m  700.0000m    2.1467     0.       448.0285m
  800.00000m  800.0000m    2.2209     0.       448.3605m
  900.00000m  900.0000m    2.2944     0.       448.6874m
    1.00000     1.0000     2.3673     0.       449.0096m
    1.10000     1.1000     2.4396     0.       449.3271m
    1.20000     1.2000     2.5113     0.       449.6402m
    1.30000     1.3000     2.5825     0.       449.9491m
    1.40000     1.4000     2.6530     0.       450.2538m
    1.50000     1.5000     2.7231     0.       450.5546m
    1.60000     1.6000     2.7926     0.       450.8515m
    1.70000     1.7000     2.8617     0.       451.1448m
    1.80000     1.8000     2.9302     0.       451.4346m
    1.90000     1.9000     2.9983     0.       451.7209m
    2.00000     2.0000     3.0660     0.       452.0038m


 vin          voltage    voltage    voltage    voltage
             34         41         3          20
    0.          2.5000   156.4974m   -2.9768     2.5000
  100.00000m    2.5000   160.8099m   -2.9257     2.5000
  200.00000m    2.5000   165.0116m   -2.8746     2.5000
  300.00000m    2.5000   169.1043m   -2.8237     2.5000
  400.00000m    2.5000   173.0898m   -2.7729     2.5000
  500.00000m    2.5000   176.9696m   -2.7221     2.5000
  600.00000m    2.5000   180.7453m   -2.6714     2.5000
  700.00000m    2.5000   184.4181m   -2.6207     2.5000
  800.00000m    2.5000   187.9893m   -2.5701     2.5000
  900.00000m    2.5000   191.4602m   -2.5195     2.5000
    1.00000     2.5000   194.8316m   -2.4688     2.5000
    1.10000     2.5000   198.1046m   -2.4182     2.5000
    1.20000     2.5000   201.2801m   -2.3676     2.5000
    1.30000     2.5000   204.3589m   -2.3169     2.5000
    1.40000     2.5000   207.3415m   -2.2662     2.5000
    1.50000     2.5000   210.2288m   -2.2154     2.5000
    1.60000     2.5000   213.0212m   -2.1646     2.5000
    1.70000     2.5000   215.7192m   -2.1137     2.5000
    1.80000     2.5000   218.3231m   -2.0628     2.5000
    1.90000     2.5000   220.8333m   -2.0117     2.5000
    2.00000     2.5000   223.2501m   -1.9606     2.5000

 vin          voltage    voltage
             35         36
    0.          2.5000     2.5000
  100.00000m    2.5000     2.5000
  200.00000m    2.5000     2.5000
  300.00000m    2.5000     2.5000
  400.00000m    2.5000     2.5000
  500.00000m    2.5000     2.5000
  600.00000m    2.5000     2.5000
  700.00000m    2.5000     2.5000
  800.00000m    2.5000     2.5000
  900.00000m    2.5000     2.5000
    1.00000     2.5000     2.5000
    1.10000     2.5000     2.5000
    1.20000     2.5000     2.5000
    1.30000     2.5000     2.5000
    1.40000     2.5000     2.5000
    1.50000     2.5000     2.5000
    1.60000     2.5000     2.5000
    1.70000     2.5000     2.5000
    1.80000     2.5000     2.5000
    1.90000     2.5000     2.5000
    2.00000     2.5000     2.5000

* Example Current Simulation Log 1 Data *

 vin          current    current    current    current
             m81        m82        m83        m84
    0.          8.3373p    2.3669p   -1.1327m    1.6268u
  100.00000m    8.3328p    2.3656p   -1.1187m    1.6178u
  200.00000m    8.3287p    2.3644p   -1.1042m    1.6096u
  300.00000m    8.3247p    2.3633p   -1.0893m    1.6018u
  400.00000m    8.3209p    2.3622p   -1.0740m    1.5945u
  500.00000m    8.3174p    2.3612p   -1.0582m    1.5876u
  600.00000m    8.3139p    2.3602p   -1.0419m    1.5811u
  700.00000m    8.3107p    2.3593p   -1.0253m    1.5751u
  800.00000m    8.3076p    2.3585p   -1.0082m    1.5694u
  900.00000m    8.3047p    2.3576p -990.7726u    1.5642u
    1.00000     8.3020p    2.3568p -972.9501u    1.5593u
    1.10000     8.2993p    2.3561p -954.7595u    1.5548u
    1.20000     8.2969p    2.3554p -936.2107u    1.5507u
    1.30000     8.2946p    2.3548p -917.3133u    1.5470u
    1.40000     8.2925p    2.3541p -898.0763u    1.5436u
    1.50000     8.2905p    2.3536p -878.5084u    1.5405u
    1.60000     8.2886p    2.3531p -858.6179u    1.5378u
    1.70000     8.2869p    2.3526p -838.4125u    1.5355u
    1.80000     8.2853p    2.3521p -817.8998u    1.5335u
    1.90000     8.2839p    2.3517p -797.0869u    1.5318u
    2.00000     8.2826p    2.3513p -775.9808u    1.5305u


 vin          current    current    current    current
             m2         m6         m4         m3
    0.         57.4132u   22.3197u  740.9825u  259.0175u
  100.00000m   57.4538u   22.9095u  752.2856u  247.8762u
  200.00000m   57.4933u   23.4749u  763.1730u  236.9864u
  300.00000m   57.5320u   24.0240u  773.8153u  226.3418u
  400.00000m   57.5700u   24.5573u  784.2154u  215.9397u
  500.00000m   57.6074u   25.0749u  794.3758u  205.7774u
  600.00000m   57.6442u   25.5773u  804.2987u  195.8528u
  700.00000m   57.6803u   26.0648u  813.9859u  186.1641u
  800.00000m   57.7159u   26.5375u  823.4389u  176.7098u
  900.00000m   57.7510u   26.9957u  832.6589u  167.4886u
    1.00000    57.7855u   27.4398u  841.6468u  158.4995u
    1.10000    57.8195u   27.8698u  850.4034u  149.7420u
    1.20000    57.8531u   28.2861u  858.9290u  141.2155u
    1.30000    57.8861u   28.6888u  867.2239u  132.9199u
    1.40000    57.9188u   29.0780u  875.2880u  124.8552u
    1.50000    57.9510u   29.4540u  883.1211u  117.0216u
    1.60000    57.9827u   29.8169u  890.7227u  109.4196u
    1.70000    58.0141u   30.1668u  898.0920u  102.0501u
    1.80000    58.0451u   30.5039u  905.2281u   94.9137u
    1.90000    58.0757u   30.8282u  912.1300u   88.0118u
    2.00000    58.1060u   31.1399u  918.7961u   81.3457u


 vin          current    current    current    current
             m8         m9         m7         m5
    0.        -90.1233u -189.1853u -532.7645u   22.3197u
  100.00000m  -90.9495u -194.8477u -526.3232u   22.9063u
  200.00000m  -91.7184u -200.2850u -519.5571u   23.4719u
  300.00000m  -92.4512u -205.6050u -512.4180u   24.0211u
  400.00000m  -93.1492u -210.8085u -504.9268u   24.5545u
  500.00000m  -93.8134u -215.8966u -497.1030u   25.0722u
  600.00000m  -94.4449u -220.8697u -488.9643u   25.5747u
  700.00000m  -95.0447u -225.7285u -480.5275u   26.0622u
  800.00000m  -95.6135u -230.4734u -471.8078u   26.5350u
  900.00000m  -96.1522u -235.1046u -462.8195u   26.9934u
    1.00000   -96.6613u -239.6223u -453.5758u   27.4375u
    1.10000   -97.1414u -244.0265u -444.0892u   27.8677u
    1.20000   -97.5932u -248.3173u -434.3712u   28.2840u
    1.30000   -98.0170u -252.4945u -424.4326u   28.6868u
    1.40000   -98.4133u -256.5577u -414.2836u   29.0762u
    1.50000   -98.7824u -260.5066u -403.9337u   29.4522u
    1.60000   -99.1246u -264.3408u -393.3919u   29.8152u
    1.70000   -99.4401u -268.0597u -382.6666u   30.1652u
    1.80000   -99.7292u -271.6627u -371.7658u   30.5024u
    1.90000   -99.9920u -275.1489u -360.6969u   30.8268u
    2.00000  -100.2286u -278.5175u -349.4671u   31.1386u

 vin          current    current
             m1         m10
    0.         57.4132u -448.2028u
  100.00000m   57.4538u -442.5197u
  200.00000m   57.4932u -437.0729u
  300.00000m   57.5319u -431.7534u
  400.00000m   57.5700u -426.5595u
  500.00000m   57.6074u -421.4895u
  600.00000m   57.6441u -416.5420u
  700.00000m   57.6803u -411.7156u
  800.00000m   57.7159u -407.0093u
  900.00000m   57.7510u -402.4223u
    1.00000    57.7855u -397.9536u
    1.10000    57.8195u -393.6027u
    1.20000    57.8530u -389.3692u
    1.30000    57.8861u -385.2527u
    1.40000    57.9187u -381.2529u
    1.50000    57.9509u -377.3699u
    1.60000    57.9827u -373.6036u
    1.70000    58.0141u -369.9541u
    1.80000    58.0451u -366.4218u
    1.90000    58.0757u -363.0070u
    2.00000    58.1059u -359.7102u

Desired output voltage specifications:

The voltage at output node 'out' should be less than 0.36V for Vin between 0V and 2V.
"""
paragraph_example_explanation_1 = """Netlist 1 contains a Trojan. The Trojan is:

Cunit 4 0 50pF
Cmain y 0 90pF
M80 4 3 VDD VDD PMOS W=0.5u L=0.1u
M81 4 3 y 0 NMOS W=0.5u L=0.1u
M82 y 0 0 0 NMOS W=0.1u L=0.1u
M83 1 y VDD VDD PMOS W=0.1u L=0.1u
M84 1 y 0 0 NMOS W=0.1u L=0.1u

The node 3 is the trigger node of the Trojan that is inserted in the netlist. The node 4 is the input node of the Trojan and node 1 is the Trojan payload.
The output voltage at node 7 exceeds the desired specification when vin becomes 0.3V. We follow the steps from voltage simulation log to obtain the list of Trojan-impacted nodes. We observe that node 1 voltage starts to show significant increase when the output voltage exceeds the desired specification.
Voltages at nodes 3 and 4 also starts decreasing when the output voltage exceeds the desired specification. Therefore, these nodes are Trojan-impacted nodes.

Next, we follow the steps from current simulation log to obtain the Trojan-impacted nodes with more confidence. We observe that when output voltage exceeds desired specification, current at MOSFET m8 increases abruptly.
This justifies Kirchoff's law, suggesting Trojan input node is 3. Due to insertion of Trojan, m8 draws more current.
"""
conv.add_message("user", paragraph_example_1)
conv.add_message("assistant", paragraph_example_explanation_1)


import os

def spice_netlist(file_path):
  with open(file_path, 'r') as file:
    return file.read()
def load_simulation_log(file_path):
    with open(file_path, 'r') as file:
        return file.read()
def submit_simulation_data(netlist_path, current_log_path, voltage_log_path):
    netlist = spice_netlist(netlist_path)
    current_log = load_simulation_log(current_log_path)
    voltage_log = load_simulation_log(voltage_log_path)


    new_task= f"""
    Now that you have learned and understood the above two examples, you have the knowledge to identify a Trojan circuit in a SPICE netlist.
    You will be provided with a new SPICE netlist, its corresponding simulation log file, and the desired specifications for the primary output voltage behavior. Follow 'Steps for Voltage Simulation Log' and 'Steps for Current Simulation Log' to perform the following tasks:

    1. **Identify the Trojan**: Based on the Trojan circuit shown in the above example, analyze the new SPICE netlist shown below  and check if you can detect similar Trojan lines.

    2. **Identify the Impacted Nodes**: Once you have identified the presence of a Trojan, list all the nodes in the netlist that are affected by the Trojan. These are the nodes where abnormal behaviors in the MOSFETs (such as unexpected current or voltage characteristics) have been observed. Provide a detailed list of these nodes.
    3. **List all the specific input voltages that cause anomalies in the impacted nodes, and provide a comprehensive explanation of how these factors contribute to the abnormal current and voltage behavior observed in the nodes.
    4. **Provide confidence score**: Can you show the formula you use to generate the confidence score? Based on the formula, generate a confidence score between 0 and 1 based on the voltage and current deviation for the impacted nodes obtained from previous step. For example, if there are two suspect nodes 1 and 2, and node 1 shows higher abnormal voltage deviation than node 2, assign a higher confidence score to 1. List the confidence score of the Trojan-impacted nodes in the format: "Confidence score_<node_name>: <score>"


    New Netlist:
    {netlist}

    New Current Simulation Log:
    {current_log}

    New Voltage Simulation Log:
    {voltage_log}

    Desired output voltage specification:
    The voltage at node 'out' should be 1.3V for vin between 0V and 1.8V.
    """


    conv.add_message("user", new_task)

# Generate the response
    response = generate_verilog(conv, "ChatGPT3p5")
    conv.add_message("assistant", response)


    return response

# Directory containing the cases
cases_dir = '/home/jchaudh3/LLM_Trojan_det/738/'

# List all files in the directory
all_files = os.listdir(cases_dir)

# Function to determine corresponding files for each case
def get_case_files(files, case_id):
    netlist_path = None
    current_log_path = None
    voltage_log_path = None
    for file in files:
        if f"738_trojan_{case_id}.cir" in file:

            netlist_path = os.path.join(cases_dir, file)
        elif f"738_trojan_{case_id}_current.lis" in file:
            current_log_path = os.path.join(cases_dir, file)
        elif f"738_trojan_{case_id}_voltage.lis" in file:
            voltage_log_path = os.path.join(cases_dir, file)
    return netlist_path, current_log_path, voltage_log_path

# Determine the number of cases based on file naming convention
  # Adjust this based on the actual number of cases

# Iterate over each case and submit the simulation data
for case_id in range(1, 13):
    netlist_path, current_log_path, voltage_log_path = get_case_files(all_files, case_id)

    if netlist_path and current_log_path and voltage_log_path:
        print("pass")
        response = submit_simulation_data(netlist_path, current_log_path, voltage_log_path)
        print(f"Response for case {case_id}:")
        print(response)
        print("\n" + "="*50 + "\n")
    else:
        print("Continue")
    conv.remove_message(10)


