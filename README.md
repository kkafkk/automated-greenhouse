# Automated Urban Greenhouse System

## About the Project
This project is an automated system designed for growing mushrooms, microgreens, berries, and other crops in an urban environment[cite: 1]. Built around a Raspberry Pi 3B+ microcomputer, the system autonomously maintains the optimal microclimate for plant growth[cite: 1]. It reduces the time required for human monitoring by 90% and increases crop yield by 15–20% compared to manual care[cite: 1]. 

## Key Features
*   **Multi-Crop Support:** Includes 8 pre-programmed modes for different types of cultures[cite: 1].
*   **Triple Interface Control:** The system can be monitored and controlled via a Web server (FastAPI), a Telegram Bot (aiogram), and a local E-paper display[cite: 1].
*   **Computer Vision:** Utilizes OpenCV to analyze the color of the plants/mushrooms from a camera feed, determining harvest readiness with 85–90% accuracy[cite: 1].
*   **Smart Notifications:** Consolidates alert messages via Telegram to avoid spamming the user, limiting repeated warnings to once per hour[cite: 1].

## Hardware Components
The hardware architecture is designed to be cost-effective and reliable, with a total prototype cost of around 7,800 RUB[cite: 1].
*   **Core:** Raspberry Pi 3B+[cite: 1].
*   **Sensors:** 
    *   DHT-22 (Temperature & Humidity)[cite: 1].
    *   YL-018 (Soil Moisture)[cite: 1].
    *   MQ-135 (CO2 / Gas)[cite: 1].
    *   KY-018 (Light Level)[cite: 1].
*   **Modules & Actuators:**
    *   PCF8591 ADC module for analog sensors[cite: 1].
    *   Peltier elements (TEC1-12703) and fans for climate control[cite: 1].
    *   MOSFETs (IRLZ44N, IRLZ34N) and relay modules for silent and safe power management[cite: 1].
*   **Housing:** Modular case designed in KOMPAS-3D and 3D-printed using moisture-resistant HIPS and PETG plastics[cite: 1].

## Repository Structure
*   `/3d-models/` - 3D printable files for the greenhouse housing.
*   `/drawings/` - Technical drawings of the components.
*   `/src/` - Python source code for the control system, Web UI, and Telegram bot.
*   `/docs/` - Connection diagrams and specifications.
*   `/media/` - Photos and video demonstrations of the system in action.


## Author
Katya — @kkafkk
