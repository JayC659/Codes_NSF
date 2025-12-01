SPICED/SPICED+/LATENT 

This repository bundles three Python scripts analog/mixed-signal (A/MS) Trojan generation and detection workflows:

- **SPICED** (spiced.py): LLM‑assisted *Trojan detection and localization*: reads SPICE netlist, simulation logs, and employs a supervised learning-based Chain-of-Thought (CoT) approach along with few-shot learning for effective Trojan detection.
- **SPICED+** (spiced_plus.py): An agent‑style detector with iterative analysis for *Trojan mitigation*.
- **LATENT** (latent.py): LLM agent-guided *generation/insertion* pipeline (e.g., Trojan candidate synthesis).


## Requirements

- **Python 3.9+** 
- Recommended: a virtual environment (e.g., `venv` or Conda)
- Packages (minimal set):
  ```bash
  pip install openai 
  ```
- Include HSPICE in your PATH**
- Create an OPENAI_API_KEY  if using the OpenAI backend**



## Citation

If you use this toolkit in academic work, please cite the following papers associated with this codebase.
1. Chaudhuri, Jayeeta, et al. "Spiced: Syntactical bug and trojan pattern identification in a/ms circuits using llm-enhanced detection." 2024 IEEE Physical Assurance and Inspection of Electronics (PAINE). IEEE, 2024.
2. Chaudhuri, Jayeeta, et al. "Spiced+: Syntactical bug pattern identification and correction of trojans in a/ms circuits using llm-enhanced detection." IEEE Transactions on Very Large Scale Integration (VLSI) Systems (2025).
3. Chaudhuri, Jayeeta, Arjun Chaudhuri, and Krishnendu Chakrabarty. "LATENT: LLM-Augmented Trojan Insertion and Evaluation Framework for Analog Netlist Topologies." arXiv preprint arXiv:2505.06364 (2025).


