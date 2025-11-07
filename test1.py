"""
FriskaAi - Simplified Streamlit App
Refactored to be self-contained (no Excel, no local media/files).
- Uses a small hardcoded ExerciseDatabase
- Keeps AI API call scaffolding (API_KEY and ENDPOINT_URL are placeholders)
- Provides a robust local fallback generator if the API fails
- Preserves full intake form, BMI calculation, validation, download, and feedback

Run: streamlit run app.py
"""

# ---------------- IMPORTS & CONFIG ----------------
from typing import Dict, List, Optional
import requests
import streamlit as st

# Replace these with your real API key & endpoint when deploying
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"

st.set_page_config(page_title="FriskaAi - Smart Fitness Advisor", layout="wide")


# ---------------- EXERCISE DATABASE (HARD-CODED) ----------------
@st.cache_data
def get_exercise_db() -> Dict[str, Dict]:
    """
    Returns a small, hard-coded exercise database (text-only).
    Kept intentionally compact (5-7 exercises) for clarity and offline use.
    """
    exercises = {
        "dead_bug": {
            "name": "Supine Dead Bug",
            "type": "Core Stability",
            "equipment": ["Mat"],
            "level": "Beginner",
            "reps": "8-12 reps/side",
            "intensity": "RPE 3-4",
            "rest": "30-45 sec",
            "benefits": "Improves core control and lumbar stability.",
            "target_areas": ["Core", "Stomach"],
            "rating": 4.5,
            "safety": "Keep a neutral spine. Stop if sharp back pain occurs.",
            "contraindications": ["acute lower back pain", "recent spinal surgery"],
            "steps": [
                "Lie on your back with knees bent and feet off the floor.",
                "Slowly extend opposite arm and leg while keeping core braced.",
                "Hold briefly, then return and switch sides."
            ],
            "common_mistakes": ["Arching the back", "Using momentum"]
        },
        "bird_dog": {
            "name": "Bird Dog",
            "type": "Core & Stability",
            "equipment": ["Mat"],
            "level": "Beginner",
            "reps": "8-12 reps/side",
            "intensity": "RPE 3-5",
            "rest": "30-45 sec",
            "benefits": "Builds posterior chain stability and core control.",
            "target_areas": ["Core", "Back", "Glutes"],
            "rating": 4.6,
            "safety": "Avoid if you have severe recent spinal injury without clearance.",
            "contraindications": ["recent spinal surgery"],
            "steps": [
                "Start on hands and knees with neutral spine.",
                "Extend opposite arm and leg until in line with torso.",
                "Hold briefly then return; repeat other side."
            ],
            "common_mistakes": ["Rotating hips", "Raising leg too high"]
        },
        "glute_bridge": {
            "name": "Glute Bridge",
            "type": "Hip Hinge / Glute Strength",
            "equipment": ["Mat"],
            "level": "Beginner",
            "reps": "10-15 reps",
            "intensity": "RPE 4-6",
            "rest": "45-60 sec",
            "benefits": "Strengthens glutes and posterior chain.",
            "target_areas": ["Glutes", "Legs", "Core"],
            "rating": 4.7,
            "safety": "Avoid excessive lumbar extension; stop if pain increases.",
            "contraindications": ["acute lower back pain"],
            "steps": [
                "Lie on your back with knees bent and feet flat.",
                "Drive through heels to lift hips until knees, hips, shoulders are in line.",
                "Lower with control."
            ],
            "common_mistakes": ["Pushing through toes", "Overarching lower back"]
        },
        "wall_push_up": {
            "name": "Wall Push-Up",
            "type": "Upper Body Strength (Low Load)",
            "equipment": ["Wall"],
            "level": "Beginner",
            "reps": "8-15 reps",
            "intensity": "RPE 3-5",
            "rest": "45-60 sec",
            "benefits": "Builds chest and shoulder strength with low load.",
            "target_areas": ["Chest", "Arms", "Shoulders"],
            "rating": 4.3,
            "safety": "Use a stable wall. Avoid if shoulder pain is aggravated.",
            "contraindications": ["acute shoulder injury"],
            "steps": [
                "Stand facing a wall with hands on wall at chest height.",
                "Bend elbows to bring chest toward wall, then press back to start."
            ],
            "common_mistakes": ["Flaring elbows", "Sagging hips"]
        },
        "bodyweight_squat": {
            "name": "Bodyweight Squat (Chair-Assisted option)",
            "type": "Lower Body Strength",
            "equipment": ["Chair (optional)"],
            "level": "Beginner to Intermediate",
            "reps": "8-15 reps",
            "intensity": "RPE 4-7",
            "rest": "60-90 sec",
            "benefits": "Builds leg strength and functional capacity.",
            "target_areas": ["Legs", "Glutes"],
            "rating": 4.6,
            "safety": "Use chair support if balance or knee pain present; stop if sharp pain.",
            "contraindications": ["acute knee injury", "recent knee surgery"],
            "steps": [
                "Stand feet shoulder-width, sit back into hips, keep chest up.",
                "Lower until comfortable (to chair if needed), then drive up through heels."
            ],
            "common_mistakes": ["Knees caving in", "Leaning too far forward"]
        },
        "standing_march": {
            "name": "Standing March (Balance & Cardio)",
            "type": "Cardio / Balance",
            "equipment": ["None"],
            "level": "Beginner",
            "reps": "1-3 minutes or 30-60 steps each side",
            "intensity": "RPE 3-5",
            "rest": "As needed",
            "benefits": "Improves balance and light cardio capacity.",
            "target_areas": ["Legs", "Core", "Balance"],
            "rating": 4.2,
            "safety": "Hold a chair for support if needed.",
            "contraindications": [],
            "steps": [
                "Stand tall and march in place lifting knees to comfortable height.",
                "Use arms for counterbalance; progress to higher cadence as tolerated."
            ],
            "common_mistakes": ["Hunching shoulders", "Not controlling movement"]
        }
    }
    return exercises


# ---------------- FITNESS ADVISOR ----------------
class FitnessAdvisor:
    """
    Core class responsible for:
    - Building the system prompt (kept simple here)
    - Sending request to external AI endpoint (scaffolded)
    - Falling back to local generator if the API is not available
    """

    def __init__(self, api_key: str = "", endpoint_url: str = ""):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.exercise_db = get_exercise_db()

    def assess_risk_flag(self, user_profile: Dict) -> str:
        """
        Simple risk assessment based on provided medical conditions and limitations.
        Returns: "None", "Low", "Moderate", or "High"
        """
        medical = [c.lower() for c in (user_profile.get("medical_conditions") or [])]
        physical = (user_profile.get("physical_limitations") or "").lower()

        high_risk_triggers = ["heart", "recent surgery", "uncontrolled", "stroke", "heart failure"]
        moderate_risk_triggers = ["diabetes", "arthritis", "osteoporosis", "copd", "obesity"]

        for hr in high_risk_triggers:
            if any(hr in m for m in medical) or hr in physical:
                return "High"
        for mr in moderate_risk_triggers:
            if any(mr in m for m in medical) or mr in physical:
                return "Moderate"

        return "Low" if medical and medical != ["none"] else "None"

    def build_system_prompt(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """
        Constructs a concise system/user prompt for the AI model.
        Note: This version avoids referencing any external files and focuses on clarifying user context.
        """
        name = user_profile.get("name", "User")
        age = user_profile.get("age", "N/A")
        fitness_level = user_profile.get("fitness_level", "Level 3 - Moderate")
        target_areas = user_profile.get("target_areas", ["Full Body"])
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        session_duration = user_profile.get("session_duration", "30-45 minutes")
        equipment = ", ".join(user_profile.get("available_equipment", ["None - Bodyweight Only"]))

        focus_area = target_areas[day_index % len(target_areas)]

        prompt = (
            f"You are a certified exercise physiologist creating a single-session workout plan.\n\n"
            f"Client: {name}, Age: {age}, Fitness level: {fitness_level}\n"
            f"Primary goal: {primary_goal}\n"
            f"Session duration: {session_duration}\n"
            f"Available equipment: {equipment}\n"
            f"Target focus for {day_name}: {focus_area}\n\n"
            "Constraints: avoid exercises that are contraindicated for common joint/heart/back conditions, "
            "prioritize safety and clear step-by-step instructions. Output must include Warm-Up, Main Workout (4-6 exercises), "
            "Cool-Down, Progression Notes, and 2-3 Safety reminders. Use markdown headers and the exercise format: name, benefit, steps, sets×reps, intensity, rest, safety, modification.\n"
            "Be concise and professional. Response language: English."
        )
        return prompt

    def send_api_request(self, prompt: str) -> Optional[str]:
        """
        Sends the prompt to the external AI endpoint. Returns the string output on success,
        or None on failure. This is a thin wrapper and uses requests.
        """
        if not self.api_key or not self.endpoint_url:
            return None

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "fitness-advisor",
            "messages": [
                {"role": "system", "content": "You are FriskaAI, an expert clinical exercise physiologist."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1500,
        }

        try:
            resp = requests.post(self.endpoint_url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                # Many LLM APIs use different shapes; attempt to extract text robustly
                choices = result.get("choices") or []
                if choices:
                    first = choices[0]
                    # Some models return message.content, some return text
                    if isinstance(first.get("message"), dict):
                        return first["message"].get("content")
                    return first.get("text") or None
        except Exception as e:
            # Do not crash the app for API failures; fallback will be used
            st.warning(f"AI API request failed: {e}")
            return None

        return None

    def generate_local_day_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """
        Local, deterministic fallback plan generator that composes a readable workout
        using the small exercise DB. This ensures the app works offline.
        """
        target_areas = user_profile.get("target_areas", ["Full Body"])
        focus = target_areas[day_index % len(target_areas)]

        # Collect candidate exercises that match focus
        exercises = list(self.exercise_db.values())
        candidates = [ex for ex in exercises if focus in ex.get("target_areas", [])]
        if not candidates:
            # If no direct matches, choose a balanced subset
            candidates = exercises[:5]

        # Basic contraindication filter
        medical_conditions = [c.lower() for c in (user_profile.get("medical_conditions") or [])]
        def is_safe(ex):
            ex_contras = [c.lower() for c in ex.get("contraindications", [])]
            for mc in medical_conditions:
                for ec in ex_contras:
                    if mc and (ec in mc or mc in ec):
                        return False
            return True

        safe = [ex for ex in candidates if is_safe(ex)]
        if not safe:
            safe = [ex for ex in exercises if is_safe(ex)]
        if not safe:
            safe = exercises[:5]

        # Sort by rating, choose top 5 or 4 depending on session length
        safe_sorted = sorted(safe, key=lambda x: -x.get("rating", 0))
        num_main = 4 if user_profile.get("session_duration", "").startswith("15-20") else 5
        main_exs = safe_sorted[:num_main]

        # Build plan text
        parts = []
        parts.append(f"### {day_name} – {focus} Focus\n")
        parts.append("**Warm-Up (5-7 minutes)**")
        parts.append("- Marching on the spot (1-2 minutes)")
        parts.append("- Arm circles and shoulder rolls (1-2 minutes)")
        parts.append("- Hip circles / leg swings (1-2 minutes)\n")

        parts.append("**Main Workout**")
        for i, ex in enumerate(main_exs, 1):
            parts.append(f"**{ex['name']}**")
            parts.append(f"- Benefit: {ex['benefits']}")
            parts.append("- How to Perform:")
            for idx, step in enumerate(ex.get("steps", []), 1):
                parts.append(f"  {idx}. {step}")
            parts.append(f"- Sets × Reps: {ex.get('reps')}")
            parts.append(f"- Intensity: {ex.get('intensity')}")
            parts.append(f"- Rest: {ex.get('rest')}")
            parts.append(f"- Safety Cue: {ex.get('safety')}")
            parts.append(f"- Modification: Use assisted/chair version if needed.\n")

        parts.append("**Cool-Down (5-7 minutes)**")
        parts.append("- Standing hamstring stretch (1-2 minutes)")
        parts.append("- Chest opener against wall (1-2 minutes)")
        parts.append("- Controlled diaphragmatic breathing (1-2 minutes)\n")

        parts.append("**Progression for Next Week:**")
        parts.append("- Slightly increase reps (by 1-3) or add another set if comfortable.")
        parts.append("- Prioritize form; do not increase intensity if pain occurs.\n")

        parts.append("**KEY SAFETY REMINDERS:**")
        parts.append("- Stop if you experience sharp pain, dizziness, or unusual breathlessness.")
        parts.append("- Modify exercises to a seated or supported variation if needed.")
        parts.append("- Consult a healthcare professional if you have medical concerns.\n")

        return "\n".join(parts)

    def generate_day_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """
        Tries to generate a plan using the external API first. If that fails, falls back
        to the local generator.
        """
        # Build a concise prompt for the AI
        prompt = self.build_system_prompt(user_profile, day_name, day_index)

        # Attempt API call
        api_response = self.send_api_request(prompt)
        if api_response:
            return api_response.strip()

        # Fallback local plan
        return self.generate_local_day_plan(user_profile, day_name, day_index)

    def generate_full_plan(self, user_profile: Dict) -> str:
        """
        Assemble a multi-day plan by generating each selected day's session.
        Keeps user informed with simple progress indicators.
        """
        days = user_profile.get("selected_days", ["Monday", "Wednesday", "Friday"])
        header = (
            f"# 🏋️‍♂️ Your Personalized Fitness Plan\n\n"
            f"**👋 Hello {user_profile.get('name', 'there')}!**\n\n"
            f"- Age: {user_profile.get('age')} | Fitness Level: {user_profile.get('fitness_level')}\n"
            f"- Primary Goal: {user_profile.get('primary_goal')}\n"
            f"- Training Schedule: {len(days)} days/week ({', '.join(days)})\n"
            f"- Location: {user_profile.get('workout_location')}\n\n"
            + "---\n"
        )

        body = [header]
        progress_placeholder = st.empty()

        for idx, day in enumerate(days):
            progress_placeholder.info(f"Generating plan for {day}... ({idx+1}/{len(days)})")
            day_plan = self.generate_day_plan(user_profile, day, idx)
            body.append(day_plan)
            body.append("\n---\n")

        progress_placeholder.success(f"All {len(days)} workout days generated!")
        footer = (
            "## 📈 Progression Tips\n"
            "- Week 1-2: Focus on technique and consistency\n"
            "- Week 3+: Increase volume slowly (more reps/sets) or add light resistance\n\n"
            "## 💧 Safety & Reminders\n"
            "- Stay hydrated and stop if you feel unwell.\n"
            "- Get medical clearance if you have major health concerns.\n"
        )
        body.append(footer)
        return "\n".join(body)


# ---------------- STREAMLIT UI FORM ----------------
fitness_advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)

if 'fitness_plan' not in st.session_state:
    st.session_state.fitness_plan = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None

st.title("🏋️‍♂️ FriskaAi - Your Personal Fitness Advisor")
st.markdown("**Personalized health & function plan for special populations.**")
st.markdown("---")

# Medical Conditions list (kept inline so there's no external dependency)
MEDICAL_CONDITIONS = [
    "None",
    "Hypertension (High Blood Pressure)",
    "Type 2 Diabetes",
    "Coronary Artery Disease",
    "Osteoarthritis",
    "Chronic Lower Back Pain",
    "Obesity",
    "Asthma",
    "COPD (Chronic Obstructive Pulmonary Disease)",
    "Osteoporosis",
    "Depression/Anxiety",
    "Stroke (Post-Recovery)",
    "Heart Failure",
    "Peripheral Artery Disease",
    "Rheumatoid Arthritis",
    "Sleep Apnea",
    "Chronic Kidney Disease",
    "Fatty Liver Disease",
    "PCOS (Polycystic Ovary Syndrome)",
    "Fibromyalgia",
    "Multiple Sclerosis",
    "Parkinson's Disease",
    "Cancer (During/Post Treatment)",
    "Other"
]

with st.form("fitness_intake_form"):
    # ----- Basic Info -----
    st.header("👤 Basic Information & Measurements")
    name = st.text_input("What's your name?*")
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age*", 16, 100, 30)
    with col2:
        gender = st.selectbox("Gender*", ["Male", "Female", "Other"])

    st.subheader("📏 Physical Measurements")
    col3, col4 = st.columns(2)
    with col3:
        unit_system = st.radio("Measurement System*", ["Metric (kg, cm)", "Imperial (lbs, inches)"])
    is_metric = "Metric" in unit_system

    col5, col6 = st.columns(2)
    with col5:
        if is_metric:
            height = st.number_input("Height (cm)*", 100, 250, 170)
        else:
            height = st.number_input("Height (inches)*", 39, 98, 67)
    with col6:
        if is_metric:
            weight = st.number_input("Weight (kg)*", 30.0, 300.0, 70.0, step=0.5)
        else:
            weight = st.number_input("Weight (lbs)*", 66.0, 660.0, 154.0, step=0.5)

    # BMI calculation
    if is_metric:
        bmi = weight / ((height / 100) ** 2)
    else:
        bmi = (weight / (height ** 2)) * 703
    bmi = round(bmi, 1)
    if bmi < 18.5:
        bmi_category = "Underweight"
    elif 18.5 <= bmi < 25:
        bmi_category = "Normal weight"
    elif 25 <= bmi < 30:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obese"

    st.info(f"**Your BMI:** {bmi} ({bmi_category})")
    st.markdown("---")

    # ----- Goals & Targets -----
    st.header("🎯 Your Goals & Target Areas")
    goal_options = [
        "Weight Loss",
        "Muscle Gain",
        "Increase Overall Strength",
        "Improve Cardiovascular Fitness",
        "Improve Flexibility & Mobility",
        "Rehabilitation & Injury Prevention",
        "Improve Posture and Balance",
        "Other"
    ]
    primary_goal = st.selectbox("Choose ONE primary goal*", goal_options)
    primary_goal_other = ""
    if primary_goal == "Other":
        primary_goal_other = st.text_input("Please specify your primary goal*")

    secondary_goal_options = [
        "Energy & Stamina", "Flexibility", "Stress Reduction",
        "Healthy Habits", "Confidence & Quality of Life", "Weight Management"
    ]
    secondary_goals = st.multiselect("Secondary goals (optional):", secondary_goal_options)

    target_options = ["Full Body", "Core", "Legs", "Arms", "Back", "Chest", "Shoulders", "Glutes", "Stomach"]
    target_areas = st.multiselect("Target Areas (1-3)*:", target_options, default=["Full Body"])

    doctor_clearance = "Unknown"
    rehab_stage = None
    if "Rehabilitation" in primary_goal:
        st.info("⚕️ Rehabilitation requires medical clearance")
        doctor_clearance = st.selectbox("Doctor clearance?*", ["Unknown", "Yes - I have clearance", "No - Not yet cleared"])
        if doctor_clearance == "Yes - I have clearance":
            rehab_stage = st.selectbox("Rehab Stage*", ["Phase 1 (Early/Acute)", "Phase 2 (Progressive)", "Phase 3 (Advanced)"])
    st.markdown("---")

    # ----- Health & Medical Screening -----
    st.header("🏥 Health & Medical Screening")
    st.warning("⚠️ Please consult your healthcare provider before starting any new exercise program.")
    medical_conditions = st.multiselect("Do you have any of these medical conditions?*", MEDICAL_CONDITIONS, default=["None"])
    medical_other = ""
    if "Other" in medical_conditions:
        medical_other = st.text_input("Please specify other medical condition(s)*")
    st.subheader("💊 Current Medications")
    takes_medication = st.radio("Are you currently taking any medications?*", ["No", "Yes"])
    medication_list = ""
    if takes_medication == "Yes":
        medication_list = st.text_area("Please list your medications (one per line):", placeholder="e.g., Blood pressure medication")
    physical_limitations = st.text_area("Do you have any physical limitations or injuries?", placeholder="e.g., Recent knee surgery, chronic back pain...")
    st.markdown("---")

    # ----- Activity & Lifestyle -----
    st.header("🚶 Activity & Lifestyle Assessment")
    activity_level_options = [
        "Sedentary (little to no exercise)",
        "Lightly Active (light exercise 1-3 days/week)",
        "Moderately Active (moderate exercise 3-5 days/week)",
        "Very Active (intense exercise 6-7 days/week)",
        "Extremely Active (physical job + intense exercise)"
    ]
    current_activity = st.selectbox("Current Activity Level*", activity_level_options)
    col7, col8 = st.columns(2)
    with col7:
        stress_level = st.selectbox("Daily Stress Level*", ["Low", "Moderate", "High", "Very High"])
    with col8:
        sleep_quality = st.selectbox("Sleep Quality*", ["Poor", "Fair", "Good", "Excellent"])
    sleep_hours = st.slider("Average Sleep Hours per Night*", 3, 12, 7, 1)
    st.subheader("💪 Fitness Experience")
    fitness_level_options = [
        "Level 1 – Assisted / Low Function",
        "Level 2 – Beginner Functional",
        "Level 3 – Moderate / Independent",
        "Level 4 – Active Wellness",
        "Level 5 – Adaptive Advanced"
    ]
    fitness_level = st.selectbox("Fitness Level*", fitness_level_options)
    previous_experience = st.text_area("Previous Exercise Experience (optional)", placeholder="e.g., Yoga, running, weight training...")
    st.markdown("---")

    # ----- Environment & Schedule -----
    st.header("🏠 Fitness Environment & Constraints")
    workout_location_options = ["Home", "Small Home Gym", "Large Commercial Gym", "Outdoor/Park", "Mixed (Home + Gym)"]
    workout_location = st.selectbox("Primary Workout Location*", workout_location_options)
    equipment_options = [
        "None - Bodyweight Only", "Mat", "Resistance Bands", "Dumbbells", "Kettlebells",
        "Barbell", "Pull-up Bar", "Bench", "Squat Rack", "Treadmill", "Stationary Bike"
    ]
    available_equipment = st.multiselect("Available Equipment*", equipment_options, default=["None - Bodyweight Only"])
    st.subheader("📅 Training Schedule")
    col9, col10 = st.columns(2)
    with col9:
        days_per_week = st.selectbox("Workout Frequency (days per week)*", [1, 2, 3, 4, 5, 6, 7], index=2)
    with col10:
        session_duration_options = ["15-20 minutes", "20-30 minutes", "30-45 minutes", "45-60 minutes", "60-90 minutes"]
        session_duration = st.selectbox("Preferred Session Duration*", session_duration_options, index=2)
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    selected_days = st.multiselect(f"Preferred Training Days* (Select {days_per_week})", all_days, default=all_days[:days_per_week])
    preferred_time_options = [
        "Early Morning (5-7 AM)", "Morning (7-10 AM)", "Late Morning (10 AM-12 PM)", "Afternoon (12-3 PM)",
        "Late Afternoon (3-6 PM)", "Evening (6-9 PM)", "Night (9 PM+)", "Flexible/Varies"
    ]
    preferred_time = st.selectbox("Preferred Workout Time*", preferred_time_options)
    st.markdown("---")

    # ----- Form Submission -----
    submitted = st.form_submit_button("✨ Generate My Personalized Plan", use_container_width=True)

    if submitted:
        validation_errors = []
        if not name:
            validation_errors.append("❌ Name is required")
        if not target_areas:
            validation_errors.append("❌ Please select at least one target area")
        if "Other" in medical_conditions and not medical_other:
            validation_errors.append("❌ Please specify your other medical condition")
        if primary_goal == "Other" and not primary_goal_other:
            validation_errors.append("❌ Please specify your primary goal")
        if len(selected_days) != days_per_week:
            validation_errors.append(f"❌ Please select exactly {days_per_week} training days")

        if validation_errors:
            st.error("### Please fix the following errors:")
            for err in validation_errors:
                st.error(err)
        else:
            final_medical_conditions = medical_conditions.copy()
            if "Other" in final_medical_conditions and medical_other:
                final_medical_conditions.remove("Other")
                final_medical_conditions.append(medical_other)

            final_primary_goal = primary_goal_other if primary_goal == "Other" else primary_goal

            user_profile = {
                "name": name,
                "age": age,
                "gender": gender,
                "height": height,
                "weight": weight,
                "unit_system": unit_system,
                "bmi": bmi,
                "bmi_category": bmi_category,
                "primary_goal": final_primary_goal,
                "secondary_goals": secondary_goals,
                "target_areas": target_areas,
                "doctor_clearance": doctor_clearance,
                "rehab_stage": rehab_stage,
                "medical_conditions": final_medical_conditions,
                "takes_medication": takes_medication,
                "medication_list": medication_list,
                "physical_limitations": physical_limitations,
                "current_activity": current_activity,
                "stress_level": stress_level,
                "sleep_hours": sleep_hours,
                "sleep_quality": sleep_quality,
                "fitness_level": fitness_level,
                "previous_experience": previous_experience,
                "workout_location": workout_location,
                "available_equipment": available_equipment,
                "days_per_week": days_per_week,
                "session_duration": session_duration,
                "selected_days": selected_days,
                "preferred_time": preferred_time
            }

            # Generate plan
            with st.spinner("🎯 Analyzing your profile and generating your personalized fitness plan..."):
                st.session_state.fitness_plan = fitness_advisor.generate_full_plan(user_profile)
                st.session_state.user_profile = user_profile


# ---------------- DISPLAY GENERATED PLAN & FEEDBACK ----------------
if st.session_state.fitness_plan:
    st.success("✅ Your personalized fitness plan is ready!")
    st.markdown("---")
    st.markdown(st.session_state.fitness_plan)
    st.markdown("---")

    # Action buttons row
    col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])

    with col_a:
        plan_text = st.session_state.fitness_plan
        st.download_button(
            label="📥 Download Plan",
            data=plan_text,
            file_name=f"FriskaAi_Plan_{st.session_state.user_profile.get('name','user')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col_b:
        if st.button("🔄 Create New Plan", use_container_width=True):
            st.session_state.fitness_plan = None
            st.session_state.user_profile = None
            st.experimental_rerun()

    with col_c:
        st.markdown(
            """
            <button onclick="window.print()" style="
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 14px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 4px;
                width: 100%;
            ">🖨️ Print Plan</button>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.header("💬 Feedback")
    st.markdown("**How satisfied are you with your personalized plan?**")
    feedback_cols = st.columns(5)
    feedback_emoji = ["😞", "😐", "🙂", "😊", "🤩"]
    feedback_text = ["Very Unsatisfied", "Unsatisfied", "Neutral", "Satisfied", "Very Satisfied"]
    for i, (col, emoji, text) in enumerate(zip(feedback_cols, feedback_emoji, feedback_text)):
        with col:
            if st.button(f"{emoji}\n{text}", key=f"feedback_{i}", use_container_width=True):
                st.success(f"Thank you — you rated: {text}")

    feedback_comments = st.text_area("Additional comments or suggestions (optional):", placeholder="Tell us what you think about the plan...")
    if st.button("Submit Feedback"):
        if feedback_comments:
            st.success("✅ Thank you for your feedback! We appreciate your input.")
        else:
            st.info("Feedback submitted!")

    st.markdown("---")
    st.info(
        """
        ### ⚠️ Important Safety Reminders
        - Always consult with a healthcare provider before starting a new exercise program if you have medical conditions.
        - Stop immediately if you experience pain, dizziness, or unusual discomfort.
        - Progress gradually and prioritize form.
        """
    )

    st.markdown("---")
    st.caption(
        """
        **Disclaimer:** This fitness plan is generated using the information you provided. It is intended for informational
        purposes only and is not a substitute for professional medical advice, diagnosis, or treatment.
        """
    )

else:
    st.markdown("---")
    st.info("👆 Please fill out the form above to generate your personalized fitness plan!")
    st.markdown("### 🌟 What You'll Get:")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
            **🎯 Personalized Plan**
            - Tailored to your goals
            - Adapted to your fitness level
            - Safety-conscious
            """
        )
    with c2:
        st.markdown(
            """
            **📅 Structured Schedule**
            - Day-by-day workouts
            - Progressive guidance
            """
        )
    with c3:
        st.markdown(
            """
            **🏥 Medical Safety**
            - Simple screening
            - Conservative modifications where needed
            """
        )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p><strong>FriskaAi - Smart Fitness Advisor</strong></p>
        <p>Powered by AI (optional) | Local fallback included</p>
        <p>© 2025 FriskaAi. All rights reserved.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
