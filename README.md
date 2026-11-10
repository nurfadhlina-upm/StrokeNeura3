# StrokeCare — AI Stroke Patient Management & Hospital Intelligence

A web application for stroke patient management, diagnosis, risk prediction, treatment planning, and hospital-wide intelligence with AI recommendations. Built with Python (Flask) and SQLite.

## Features
- **Patient Registry**: Register, view, update, and manage stroke patients.
- **Clinical Assessment**: Track stroke type, NIHSS score, onset time, symptoms, and neuroimaging.
- **AI Risk Engine**: Automated stroke recurrence risk scoring based on comorbidities and clinical vitals.
- **Evidence-Based Recommendations**: Personalized medication, acute intervention, rehabilitation, and lifestyle suggestions following AHA/ASA guidelines.
- **Hospital Intelligence**: Population-level dashboard providing real-time alerts, risk stratification, and hospital-wide AI recommendations.

## Setup & Running

1. **Install Dependencies**:
   ```bash
   pip install flask
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access via Browser**:
   - Patient Dashboard: `http://localhost:5050`
   - Hospital Intelligence: `http://localhost:5050/intelligence`
