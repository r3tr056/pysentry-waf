# PySentry WAF


**PySentry WAF** is a Python-based Flask microservice that runs on a server and provides real-time analysis and protection for web applications. Built as a personal project, it leverages machine learning (ML) techniques to analyze incoming traffic by sniffing network packets and making predictions based on a trained ML model. **Please note that PySentry WAF is intended for educational and experimental purposes only and is not recommended for production-grade deployment.**

## Features

- **Real-time Traffic Analysis:** Captures and inspects network traffic to identify potential threats and attacks on web applications.
- **Machine Learning Model:** Utilizes a pre-trained ML model to classify traffic and predict its maliciousness.
- **Customizable Rule Set:** Allows you to define and configure custom rules to enhance detection and protection capabilities.
- **Logging and Reporting:** Generates detailed logs and reports for analyzed traffic, including identified threats, classification results, and other relevant information.
- **Integration with Flask:** Built as a Flask microservice, making it easy to integrate into existing Flask-based web applications.

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.0.1-green)
![scikit-learn](https://img.shields.io/badge/scikit--learn-0.24.2-orange)
![Scapy](https://img.shields.io/badge/Scapy-2.4.5-brightgreen)


## Installation and Setup

1. Clone the repository:  
   `git clone https://github.com/r3tr056/pysentry-waf.git`
2. Install the required dependencies:  
   `pip install -r requirements.txt`
3. Configure the PySentry WAF settings in the `waf/config.py` file, including the network interface, ML model path, and other options.
4. Start the PySentry WAF service:  
   `python waf/app.py`


## Usage

1. Ensure that the PySentry WAF service is running and listening on the specified network interface and port.
2. Integrate the WAF with your web application by directing incoming traffic to PySentry WAF’s endpoint or by configuring it as a reverse proxy.
3. The WAF will analyze the incoming traffic, classify it using the ML model, and apply the defined rules to identify and mitigate potential threats.
4. Monitor the PySentry WAF logs and reports for any detected threats or suspicious activities.


## Contributing

Contributions to the PySentry WAF project are welcome! If you have any ideas, bug reports, or feature requests, please submit them via GitHub issues. You can also submit pull requests with code improvements or additional functionality.

## License

The PySentry WAF project is a personal project and is licensed under the [MIT License](LICENSE).

## Acknowledgements

- **PySentry WAF** makes use of various open-source libraries and tools, including Flask, scikit-learn, and Scapy. We acknowledge and thank the developers of these projects for their valuable contributions.

## Disclaimer

**PySentry WAF** is a personal project developed for learning and experimentation purposes. It is not intended to be a fully production-grade solution. Users deploying this tool should thoroughly test and customize it according to their environment and security requirements before considering any production use.

## Contact

For any questions, feedback, or inquiries regarding this personal project, please contact me at [dangerankur56@gmail.com](mailto:dangerankur56@gmail.com).
