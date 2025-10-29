import streamlit as st
import requests
import json
import os
import pandas as pd
from typing import Dict, List, Optional
import re
import random


condition_data = pd.read_excel("Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx")  # your Excel file
condition_data.fillna("", inplace=True)


# ---------------- CONFIG ----------------
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"

st.set_page_config(page_title="FriskaAi - Smart Fitness Advisor", layout="wide")

# ---------------- MEDICAL CONDITIONS LIST ----------------
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

# ---------------- EXERCISE DATABASE ----------------
class ExerciseDatabase:
    def __init__(self):
        self.exercises = {
            "supine_dead_bug": {
                "name": "Supine Dead Bug",
                "type": "Core Stability",
                "equipment": ["Mat"],
                "level": "Beginner",
                "reps": "10-12 reps/side",
                "intensity": "RPE 3-4",
                "rest": "30-45 sec",
                "benefits": "Improves core control & lumbar stability",
                "target_areas": ["Core", "Stomach"],
                "rating": 4.5,
                "safety": "Keep a neutral spine and avoid excessive lumbar extension. Stop if you feel sharp back pain.",
                "contraindications": ["acute lower back pain", "recent spinal surgery", "severe disc herniation"],
                "steps": [
                    "Lie on your back with knees bent at 90 degrees",
                    "Extend opposite arm and leg slowly",
                    "Hold for 2-3 seconds",
                    "Return to starting position",
                    "Repeat on other side"
                ],
                "demo_video": "Core Exercise_ Dead Bug 1.mp4",
                "common_mistakes": ["Arching back", "Moving too fast", "Not engaging core"]
            },
            "supine_rotator_cuff": {
                "name": "Supine Rotator Cuff",
                "type": "Shoulder Stability",
                "equipment": ["Mat", "Small Cushion"],
                "level": "Beginner",
                "reps": "10-12 reps/arm",
                "intensity": "RPE 3-4",
                "rest": "30-45 sec",
                "benefits": "Strengthens rotator cuff & improves posture",
                "target_areas": ["Arms", "Back"],
                "rating": 4.2,
                "safety": "Move slowly and keep range small if you have shoulder pain.",
                "contraindications": ["acute rotator cuff tear", "recent shoulder surgery", "severe shoulder impingement"],
                "steps": [
                    "Lie on your side with arm at 90 degrees",
                    "Place cushion under head for support",
                    "Rotate forearm up slowly",
                    "Hold briefly, then lower",
                    "Complete all reps before switching sides"
                ],
                "demo_video": "4 Supine Rotator Cuff Movements 1.mp4",
                "common_mistakes": ["Using momentum", "Rotating too far", "Not supporting head"]
            },
            "upward_facing_dog": {
                "name": "Upward Facing Dog",
                "type": "Spinal Extension",
                "equipment": ["Mat"],
                "level": "Intermediate",
                "reps": "6-8 reps / 15-30 sec holds",
                "intensity": "RPE 4-6",
                "rest": "30-60 sec",
                "benefits": "Opens chest & improves spinal flexibility",
                "target_areas": ["Back", "Chest"],
                "rating": 4.7,
                "safety": "Avoid if you have acute low back pain or recent spinal injury.",
                "contraindications": ["acute lower back pain", "recent spinal surgery"],
                "steps": [
                    "Start in plank position",
                    "Lower hips while lifting chest",
                    "Straighten arms and lift thighs off ground",
                    "Hold for 15-30 seconds",
                    "Lower back to starting position"
                ],
                "demo_video": "How to Do Upward-Facing Dog Pose in Yoga 1.mp4",
                "common_mistakes": ["Sinking shoulders", "Overarching neck", "Not engaging legs"]
            },
            "v_ups": {
                "name": "V-Ups",
                "type": "Core Strength",
                "equipment": ["Mat"],
                "level": "Intermediate",
                "reps": "AMRAP or 8-12 reps",
                "intensity": "RPE 6-7",
                "rest": "60-90 sec",
                "benefits": "Builds core strength & coordination",
                "target_areas": ["Core", "Stomach"],
                "rating": 4.3,
                "safety": "Keep neck neutral and avoid jerking.",
                "contraindications": ["acute lower back pain", "hernia"],
                "steps": [
                    "Lie flat with arms overhead",
                    "Simultaneously lift legs and torso",
                    "Try to touch toes at the top",
                    "Lower slowly with control",
                    "Keep core engaged throughout"
                ],
                "demo_video": "v_ups_demo.mp4",
                "common_mistakes": ["Using momentum", "Not controlling descent", "Straining neck"]
            },
            "dirty_dog": {
                "name": "Dirty Dog",
                "type": "Glute Strength",
                "equipment": ["Mat"],
                "level": "Beginner",
                "reps": "10-12 reps/side",
                "intensity": "RPE 4-5",
                "rest": "45-60 sec",
                "benefits": "Strengthens glutes & improves hip mobility",
                "target_areas": ["Glutes", "Legs"],
                "rating": 4.4,
                "safety": "Keep core braced and avoid excessive lumbar rotation.",
                "contraindications": ["acute lower back pain"],
                "steps": [
                    "Start on hands and knees",
                    "Keep knee bent and lift leg to side",
                    "Lift until thigh is parallel to ground",
                    "Lower slowly without touching ground",
                    "Complete all reps before switching"
                ],
                "demo_video": "dirty_dog_demo.mp4",
                "common_mistakes": ["Lifting too high", "Rotating hips", "Not keeping core stable"]
            },
            "barbell_squat": {
                "name": "Barbell Squat",
                "type": "Compound Strength",
                "equipment": ["Barbell", "Squat Rack"],
                "level": "Intermediate",
                "reps": "8-12 reps",
                "intensity": "70-75% 1RM",
                "rest": "90-120 sec",
                "benefits": "Builds overall leg strength and power",
                "target_areas": ["Legs", "Glutes", "Core"],
                "rating": 4.8,
                "safety": "Use proper set-up and avoid deep squats if you have knee pain.",
                "contraindications": ["acute knee injury", "recent knee surgery", "severe lower back pain"],
                "steps": [
                    "Position bar on upper traps",
                    "Stand with feet shoulder-width apart",
                    "Lower by pushing hips back and bending knees",
                    "Descend until thighs parallel to floor",
                    "Drive through heels to return to start"
                ],
                "demo_video": "barbell_squat_demo.mp4",
                "common_mistakes": ["Knee valgus", "Forward lean", "Partial range of motion"]
            },
            "bench_press": {
                "name": "Bench Press",
                "type": "Upper Body Strength",
                "equipment": ["Barbell", "Bench"],
                "level": "Intermediate",
                "reps": "6-10 reps",
                "intensity": "70-80% 1RM",
                "rest": "90-180 sec",
                "benefits": "Develops chest, shoulders, and triceps strength",
                "target_areas": ["Chest", "Arms", "Shoulders"],
                "rating": 4.7,
                "safety": "Use a spotter for heavy loads.",
                "contraindications": ["acute shoulder injury", "recent shoulder surgery"],
                "steps": [
                    "Lie flat on bench with feet planted",
                    "Grip bar slightly wider than shoulders",
                    "Lower bar to chest with control",
                    "Press bar up in straight line",
                    "Lock out arms at the top"
                ],
                "demo_video": "bench_press_demo.mp4",
                "common_mistakes": ["Bouncing off chest", "Uneven grip", "Arched back"]
            }
        }
    
    def get_exercises_by_target_area(self, target_areas: List[str], workout_location: str = "Home") -> Dict:
        """Filter exercises by target body areas and location"""
        filtered = {}
        for key, exercise in self.exercises.items():
            if "Full Body" in target_areas:
                filtered[key] = exercise
                continue
            if any(area in exercise.get("target_areas", []) for area in target_areas):
                filtered[key] = exercise
        return filtered
    
    def get_exercises_by_equipment(self, available_equipment: List[str], workout_location: str = "Home") -> Dict:
        """Filter exercises by available equipment"""
        filtered = {}
        for key, exercise in self.exercises.items():
            if "large gym" in workout_location.lower():
                filtered[key] = exercise
                continue
            
            reqs = [e.lower() for e in exercise.get("equipment", [])]
            avail = [a.lower() for a in (available_equipment or [])]
            
            if "none" in reqs or "bodyweight only" in reqs or "mat" in reqs:
                filtered[key] = exercise
            elif all(r in avail for r in reqs):
                filtered[key] = exercise
        return filtered

    def is_contraindicated(self, exercise: Dict, medical_conditions: List[str]) -> bool:
        """Check if exercise is contraindicated for user's conditions"""
        if not medical_conditions or medical_conditions == ["None"]:
            return False
        ex_contras = [c.lower() for c in exercise.get("contraindications", [])]
        user_conds = [c.lower() for c in medical_conditions]
        
        for uc in user_conds:
            for ec in ex_contras:
                if ec in uc or uc in ec:
                    return True
        return False

# ---------------- FITNESS ADVISOR CLASS ----------------
class FitnessAdvisor:
    def __init__(self, api_key: str, endpoint_url: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.exercise_db = ExerciseDatabase()

    def assess_risk_flag(self, user_profile: Dict) -> str:
        """Return risk_flag: None, Low, Moderate, High"""
        medical = [c.lower() for c in (user_profile.get("medical_conditions") or [])]
        physical = (user_profile.get("physical_limitations") or "").lower()
        
        high_risk = ["heart", "recent surgery", "stroke", "heart failure", "uncontrolled hypertension"]
        moderate_risk = ["diabetes", "arthritis", "osteoporosis", "obesity", "copd"]
        
        for hr in high_risk:
            if any(hr in m for m in medical) or hr in physical:
                return "High"
        for mr in moderate_risk:
            if any(mr in m for m in medical) or mr in physical:
                return "Moderate"
        
        return "Low" if medical and medical != ["none"] else "None"

    def get_condition_guidelines(self, medical_conditions: List[str]) -> str:
        guidelines = []
        for cond in medical_conditions:
            match = condition_data[condition_data["Condition"].str.contains(cond, case=False, na=False)]
            if not match.empty:
                row = match.iloc[0]
                guidelines.append(
                    f"Condition: {row['Condition']}\n"
                    f"- Avoid: {row['Contraindicated Exercises']}\n"
                    f"- Prefer: {row['Modified / Safer Exercises']}\n"
                    f"- Exercise Type: {row['Exercise Type']}\n"
                    f"- Focus Area: {row['Affected Body Region']}\n"
                    f"- Intensity: {row['Intensity Limit']}\n"
                )
        return "\n".join(guidelines) if guidelines else "No special medical restrictions found."

    def generate_exclude_tags(self, user_profile: Dict) -> List[str]:
        """Generate exercise exclusion tags"""
        tags = set()
        med = " ".join((user_profile.get("medical_conditions") or [])).lower()
        phys = (user_profile.get("physical_limitations") or "").lower()
        
        if "back" in med or "back" in phys or "disc" in med:
            tags.add("avoid_spinal_flexion")
        if "hip" in phys or "knee" in phys or "fracture" in med:
            tags.add("avoid_high_impact")
        if "cardiac" in med or "heart" in med:
            tags.add("no_heavy_isometrics")
        
        return list(tags)

    def generate_day_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """Generate one day's plan, guided by Excel condition data"""
        name = user_profile.get("name", "there")
        fitness_level = user_profile.get("fitness_level", "Level 3")
        primary_goal = user_profile.get("primary_goal", "General fitness")
        location = user_profile.get("workout_location", "Home")
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        target_areas = user_profile.get("target_areas", ["Full Body"])

        # 👇 Use the Excel condition guidelines
        condition_guidelines = self.get_condition_guidelines(medical_conditions)

        # Rotate focus by day (e.g., Core → Legs → Back → etc.)
        focus = target_areas[day_index % len(target_areas)]

        # --- Prompt for the API model ---
        prompt = f"""
    You are **FriskaAI**, a certified clinical exercise physiologist and AI fitness coach.

    ### User Profile
    - Name: {name}
    - Fitness Level: {fitness_level}
    - Goal: {primary_goal}
    - Location: {location}
    - Target Focus Today: {focus}
    - Medical Conditions & Safety Guidelines:
    {condition_guidelines}

    ### Instructions
    Design a **safe and effective workout** for users with these conditions.
    - Respect each condition’s contraindications and intensity limits.
    - Prefer modified / safer exercises listed.
    - Keep warm-up and cool-down gentle and medically safe.

    ### Output Format (strict)
    ### {day_name} - Focus: {focus}

    **Warm-up (5 min):**
    - 2–3 light movements (duration)

    **Main Workout (4–5 exercises):**
    For each exercise:
    - Exercise Name
    - Benefit
    - Sets/Reps
    - Intensity (RPE or %1RM per condition limit)
    - Rest
    - Safety Tip

    **Cool-down (5 min):**
    - 2–3 stretches or breathing drills

    Keep it under 700 tokens and easy for general users to follow.
    """

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": "fitness-advisor",
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, a concise medical fitness expert."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1200
            }

            resp = requests.post(self.endpoint_url, headers=headers, json=payload, timeout=30)

            if resp.status_code == 200:
                result = resp.json()
                choices = result.get("choices")
                if choices:
                    content = choices[0].get("message", {}).get("content") or choices[0].get("text")
                    if content:
                        return content.strip()
        except Exception as e:
            st.warning(f"API error for {day_name}: {e}")

        # --- Fallback if API fails ---
        return self.generate_local_day_plan(user_profile, day_name, day_index)


    def generate_local_day_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """Fallback local plan generator for one day"""
        target_areas = user_profile.get("target_areas", ["Full Body"])
        focus = target_areas[day_index % len(target_areas)]
        
        candidates = list(self.exercise_db.get_exercises_by_target_area([focus], 
                         user_profile.get("workout_location", "Home")).values())
        
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        safe_exercises = [ex for ex in candidates if not self.exercise_db.is_contraindicated(ex, medical_conditions)]
        
        if not safe_exercises:
            safe_exercises = list(self.exercise_db.exercises.values())[:5]
        
        safe_exercises = sorted(safe_exercises, key=lambda x: -x.get("rating", 0))[:5]
        
        plan = [f"### {day_name} - Focus: {focus}\n"]
        plan.append("**Warm-up (5 minutes):**")
        plan.append("- Jumping Jacks (2 min)")
        plan.append("- Arm Circles (1 min)")
        plan.append("- Leg Swings (2 min)\n")
        
        plan.append("**Main Workout:**\n")
        for i, ex in enumerate(safe_exercises, 1):
            plan.append(f"**{i}. {ex['name']}**")
            plan.append(f"- Benefit: {ex['benefits']}")
            plan.append(f"- Sets/Reps: {ex['reps']}")
            plan.append(f"- Intensity: {ex['intensity']}")
            plan.append(f"- Rest: {ex['rest']}")
            plan.append(f"- Safety: {ex['safety']}\n")
        
        plan.append("**Cool-down (5 minutes):**")
        plan.append("- Child's Pose (2 min)")
        plan.append("- Hamstring Stretch (2 min)")
        plan.append("- Shoulder Stretch (1 min)")
        
        return "\n".join(plan)

    def generate_full_plan(self, user_profile: Dict) -> str:
        """Generate complete workout plan day by day"""
        selected_days = user_profile.get("selected_days", ["Monday", "Wednesday", "Friday"])
        
        header = f"""# 🏋️‍♂️ Your Personalized Fitness Plan

**👋 Hey {user_profile.get('name', 'there')}!**

**📊 Your Profile:**
- Age: {user_profile.get('age')} | Fitness Level: {user_profile.get('fitness_level')}
- Primary Goal: {user_profile.get('primary_goal')}
- Training Schedule: {len(selected_days)} days/week ({', '.join(selected_days)})
- Location: {user_profile.get('workout_location')}

---

"""
        
        all_plans = [header]
        
        progress_placeholder = st.empty()
        
        for idx, day in enumerate(selected_days):
            progress_placeholder.info(f"⏳ Generating plan for {day}... ({idx+1}/{len(selected_days)})")
            day_plan = self.generate_day_plan(user_profile, day, idx)
            all_plans.append(day_plan)
            all_plans.append("\n---\n")

        
        progress_placeholder.success(f"✅ All {len(selected_days)} workout days generated!")
        
        footer = """
## 📈 Progression Tips
- Week 1-2: Focus on form and consistency
- Week 3-4: Increase reps by 2-3 or add 5% weight
- Week 5+: Add variations or increase intensity

## 💪 Stay Consistent!
Remember: Progress takes time. Listen to your body and adjust as needed.

## 💧 Hydration & Safety
- Drink water before, during, and after workouts
- Stop immediately if you feel sharp pain
- Consult your doctor if you have concerns
"""
        all_plans.append(footer)
        
        return "\n".join(all_plans)

# Initialize
fitness_advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)

# Initialize session state
if 'onboarding_step' not in st.session_state:
    st.session_state.onboarding_step = 0
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}

# Progress indicator
def show_progress():
    total_steps = 7
    current = st.session_state.onboarding_step
    progress = current / total_steps
    st.progress(progress)
    st.caption(f"Step {current} of {total_steps}")

# Navigation buttons
def nav_buttons(show_back=True, show_next=True, next_label="Next →"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if show_back and st.session_state.onboarding_step > 0:
            if st.button("← Back"):
                st.session_state.onboarding_step -= 1
                st.rerun()
    with col3:
        if show_next:
            if st.button(next_label, type="primary"):
                return True
    return False

# ============ STEP 0: WELCOME ============
if st.session_state.onboarding_step == 0:
    st.title("🏋️‍♂️ FriskaAi - Your Personal Fitness Advisor")
    st.markdown("---")
    
    st.markdown("""
    ### 👋 Welcome to FriskaAi!
    
    **Personalized health & function plan for special populations.**
    
    We create customized fitness programs that consider:
    - ✅ Your medical conditions and limitations
    - ✅ Your functional abilities and goals
    - ✅ Your available equipment and time
    - ✅ Safe progressions tailored to YOU
    
    This onboarding takes about **5-7 minutes** and will help us create the perfect plan.
    
    *Let's get started on your fitness journey!* 💪
    """)
    
    if st.button("🚀 Begin Onboarding", type="primary", use_container_width=True):
        st.session_state.onboarding_step = 1
        st.rerun()

# ============ STEP 1: BASIC INFORMATION + PHYSICAL MEASUREMENTS ============
elif st.session_state.onboarding_step == 1:
    st.title("👤 Step 1: Basic Information & Measurements")
    show_progress()
    st.markdown("*Tell us about yourself*")
    
    # Basic info
    name = st.text_input("What's your name?*", value=st.session_state.user_data.get('name', ''))
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age*", 16, 100, st.session_state.user_data.get('age', 25))
    with col2:
        gender = st.selectbox("Gender*", ["Male", "Female", "Other"], 
                             index=["Male", "Female", "Other"].index(st.session_state.user_data.get('gender', 'Male')))
    
    st.markdown("---")
    st.markdown("### 📏 Physical Measurements")
    
    col3, col4 = st.columns(2)
    
    with col3:
        unit_system = st.radio(
            "Measurement System*",
            ["Metric (kg, cm)", "Imperial (lbs, inches)"],
            index=0 if st.session_state.user_data.get('unit_system', "Metric (kg, cm)") == "Metric (kg, cm)" else 1
        )
    
    is_metric = "Metric" in unit_system
    
    col5, col6 = st.columns(2)
    
    with col5:
        if is_metric:
            height = st.number_input(
                "Height (cm)*", 
                100, 250, 
                st.session_state.user_data.get('height', 170),
                help="Enter your height in centimeters"
            )
        else:
            height = st.number_input(
                "Height (inches)*", 
                39, 98, 
                st.session_state.user_data.get('height', 67),
                help="Enter your height in inches"
            )
    
    with col6:
        if is_metric:
            weight = st.number_input(
                "Weight (kg)*", 
                30.0, 300.0, 
                st.session_state.user_data.get('weight', 70.0),
                step=0.5,
                help="Enter your weight in kilograms"
            )
        else:
            weight = st.number_input(
                "Weight (lbs)*", 
                66.0, 660.0, 
                st.session_state.user_data.get('weight', 154.0),
                step=0.5,
                help="Enter your weight in pounds"
            )
    
    # Calculate BMI
    if is_metric:
        bmi = weight / ((height / 100) ** 2)
    else:
        bmi = (weight / (height ** 2)) * 703
    
    bmi = round(bmi, 1)
    
    # BMI Category
    if bmi < 18.5:
        bmi_category = "Underweight"
        bmi_color = "blue"
    elif 18.5 <= bmi < 25:
        bmi_category = "Normal weight"
        bmi_color = "green"
    elif 25 <= bmi < 30:
        bmi_category = "Overweight"
        bmi_color = "orange"
    else:
        bmi_category = "Obese"
        bmi_color = "red"
    
    st.info(f"**Your BMI:** {bmi} ({bmi_category})")
    
    if nav_buttons(show_back=False):
        if name:
            st.session_state.user_data.update({
                'name': name, 
                'age': age, 
                'gender': gender,
                'unit_system': unit_system,
                'height': height,
                'weight': weight,
                'bmi': bmi,
                'bmi_category': bmi_category
            })
            st.session_state.onboarding_step = 2
            st.rerun()
        else:
            st.error("Please enter your name")

# ============ STEP 2: GOALS + TARGET AREAS ============
elif st.session_state.onboarding_step == 2:
    st.title("🎯 Step 2: Your Goals & Target Areas")
    show_progress()
    st.markdown("*What do you want to achieve?*")
    
    # Primary Goal
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
    
    primary_goal = st.selectbox(
        "Choose ONE primary goal*", 
        goal_options,
        index=0 if 'primary_goal' not in st.session_state.user_data else 
              goal_options.index(st.session_state.user_data.get('primary_goal', goal_options[0]))
    )
    
    # If "Other" is selected, show text input
    primary_goal_other = ""
    if primary_goal == "Other":
        primary_goal_other = st.text_input(
            "Please specify your primary goal*",
            value=st.session_state.user_data.get('primary_goal_other', ''),
            placeholder="e.g., Training for a marathon, recovering from surgery..."
        )
    
    # Secondary goals
    secondary_goal_options = [
        "Energy & Stamina",
        "Flexibility",
        "Stress Reduction",
        "Healthy Habits",
        "Confidence & Quality of Life",
        "Weight Management"
    ]
    
    secondary_goals = st.multiselect(
        "Secondary goals (optional, select multiple):",
        secondary_goal_options,
        default=st.session_state.user_data.get('secondary_goals', [])
    )
    
    st.markdown("---")
    st.markdown("### 🎯 Target Areas")
    st.markdown("*Which body areas do you want to focus on? (choose 1-3)*")
    
    target_options = [
        "Full Body", "Core", "Legs", "Arms", "Back", "Chest", 
        "Shoulders", "Glutes", "Stomach"
    ]
    
    target_areas = st.multiselect(
        "Target Areas:",
        target_options,
        default=st.session_state.user_data.get('target_areas', ["Full Body"])
    )
    
    if not target_areas:
        st.warning("Please select at least one target area")
    elif len(target_areas) > 3:
        st.info("💡 Tip: Focusing on 1-3 areas typically yields better results")
    
    # Special handling for Rehabilitation goal
    doctor_clearance = "Unknown"
    rehab_stage = None
    
    if "Rehabilitation" in primary_goal:
        st.info("⚕️ Rehabilitation requires medical clearance")
        doctor_clearance = st.selectbox("Doctor clearance?*", 
            ["Unknown", "Yes - I have clearance", "No - Not yet cleared"])
        if doctor_clearance == "Yes - I have clearance":
            rehab_stage = st.selectbox("Rehab Stage*", 
                ["Phase 1 (Early/Acute)", "Phase 2 (Progressive)", "Phase 3 (Advanced)"])
    
    if nav_buttons():
        # Validate based on primary goal selection
        if primary_goal == "Other" and not primary_goal_other:
            st.error("Please specify your primary goal")
        elif not target_areas:
            st.error("Please select at least one target area")
        else:
            final_primary_goal = primary_goal_other if primary_goal == "Other" else primary_goal
            st.session_state.user_data.update({
                'primary_goal': final_primary_goal,
                'secondary_goals': secondary_goals,
                'target_areas': target_areas,
                'doctor_clearance': doctor_clearance,
                'rehab_stage': rehab_stage
            })
            st.session_state.onboarding_step = 3
            st.rerun()

# ============ STEP 3: HEALTH & MEDICAL SCREENING ============
elif st.session_state.onboarding_step == 3:
    st.title("🥼 Step 3: Health & Medical Screening")
    show_progress()
    st.markdown("*This helps us create a safe program for you*")
    
    # Medical conditions selection
    medical_conditions = st.multiselect(
        "Select any medical conditions (select all that apply)*", 
        MEDICAL_CONDITIONS,
        default=st.session_state.user_data.get('medical_conditions', ["None"])
    )
    
    # If "Other" is selected, show text input
    medical_conditions_other = ""
    if "Other" in medical_conditions:
        medical_conditions_other = st.text_input(
            "Please specify your medical condition*",
            value=st.session_state.user_data.get('medical_conditions_other', ''),
            placeholder="e.g., Specific condition not listed above..."
        )
    
    # Current medications
    st.markdown("---")
    st.markdown("### 💊 Current Medications")
    
    taking_medications = st.radio(
        "Are you currently taking any medications?*",
        ["No", "Yes"],
        index=0 if st.session_state.user_data.get('taking_medications', 'No') == 'No' else 1
    )
    
    medications_list = ""
    if taking_medications == "Yes":
        medications_list = st.text_area(
            "Please list your medications (optional)",
            value=st.session_state.user_data.get('medications_list', ''),
            placeholder="e.g., Blood pressure medication, insulin, etc.",
            help="This helps us understand potential exercise interactions"
        )
    
    # Physical limitations
    st.markdown("---")
    st.markdown("### 🚫 Physical Limitations")
    
    physical_limitations = st.text_area(
        "Any injuries, pain, or physical limitations?*",
        value=st.session_state.user_data.get('physical_limitations', ''),
        placeholder="e.g., Lower back pain, knee injury, shoulder mobility issues...",
        help="Be specific about any areas that hurt or limit your movement"
    )
    
    if nav_buttons():
        # Validate "Other" medical condition
        if "Other" in medical_conditions and not medical_conditions_other:
            st.error("Please specify your medical condition")
        else:
            # Add "Other" condition to the list if specified
            final_medical_conditions = medical_conditions.copy()
            if "Other" in medical_conditions and medical_conditions_other:
                final_medical_conditions.remove("Other")
                final_medical_conditions.append(medical_conditions_other)
            
            st.session_state.user_data.update({
                'medical_conditions': final_medical_conditions,
                'taking_medications': taking_medications,
                'medications_list': medications_list,
                'physical_limitations': physical_limitations
            })
            st.session_state.onboarding_step = 4
            st.rerun()

# ============ STEP 4: ACTIVITY & LIFESTYLE + FITNESS LEVEL ============
elif st.session_state.onboarding_step == 4:
    st.title("📊 Step 4: Activity & Lifestyle Assessment")
    show_progress()
    st.markdown("*Help us understand your current fitness level*")
    
    # Current Activity Level (Dropdown)
    st.markdown("### 🏃 Current Activity Level")
    
    activity_level = st.selectbox(
        "How would you describe your current activity level?*",
        [
            "Sedentary (little to no exercise)",
            "Lightly Active (light exercise 1-2 days/week)",
            "Moderately Active (moderate exercise 3-4 days/week)",
            "Very Active (intense exercise 5-6 days/week)",
            "Extremely Active (intense daily exercise or physical job)"
        ],
        index=0 if 'activity_level' not in st.session_state.user_data else
              [
                  "Sedentary (little to no exercise)",
                  "Lightly Active (light exercise 1-2 days/week)",
                  "Moderately Active (moderate exercise 3-4 days/week)",
                  "Very Active (intense exercise 5-6 days/week)",
                  "Extremely Active (intense daily exercise or physical job)"
              ].index(st.session_state.user_data.get('activity_level'))
    )
    
    # Daily Stress Level (Dropdown)
    st.markdown("---")
    st.markdown("### 😰 Daily Stress Level")
    
    stress_level = st.selectbox(
        "How would you rate your daily stress level?*",
        [
            "Low (minimal stress, well-managed)",
            "Moderate (some stress, generally manageable)",
            "High (frequent stress, affecting daily life)",
            "Very High (constant stress, overwhelming)"
        ],
        index=0 if 'stress_level' not in st.session_state.user_data else
              [
                  "Low (minimal stress, well-managed)",
                  "Moderate (some stress, generally manageable)",
                  "High (frequent stress, affecting daily life)",
                  "Very High (constant stress, overwhelming)"
              ].index(st.session_state.user_data.get('stress_level', "Moderate (some stress, generally manageable)"))
    )
    
    # Sleep Quality
    col1, col2 = st.columns(2)
    
    with col1:
        sleep_hours = st.slider(
            "Average sleep hours per night*",
            4, 12, 
            st.session_state.user_data.get('sleep_hours', 7),
            help="Hours of sleep you typically get"
        )
    
    with col2:
        sleep_quality = st.selectbox(
            "Sleep quality*",
            ["Poor", "Fair", "Good", "Excellent"],
            index=["Poor", "Fair", "Good", "Excellent"].index(
                st.session_state.user_data.get('sleep_quality', 'Good')
            )
        )
    
    # Fitness Level Assessment (Dropdown - Level 1-5)
    st.markdown("---")
    st.markdown("### 💪 Fitness Level Assessment")
    
    fitness_level_descriptions = {
        "Level 1 - Beginner": "New to exercise or returning after long break. Need to build basic foundation.",
        "Level 2 - Early Intermediate": "Can do basic exercises with good form. Ready for slight progression.",
        "Level 3 - Intermediate": "Regular exerciser. Comfortable with most movements and moderate intensity.",
        "Level 4 - Advanced": "Experienced with various training methods. Can handle high intensity.",
        "Level 5 - Elite/Athlete": "Highly trained. Training at competitive or professional level."
    }
    
    fitness_level = st.selectbox(
        "Select your current fitness level*",
        list(fitness_level_descriptions.keys()),
        index=2 if 'fitness_level' not in st.session_state.user_data else
              list(fitness_level_descriptions.keys()).index(
                  st.session_state.user_data.get('fitness_level', 'Level 3 - Intermediate')
              ),
        help="Be honest - this ensures safe and effective programming"
    )
    
    st.info(f"**{fitness_level}:** {fitness_level_descriptions[fitness_level]}")
    
    # Previous Exercise Experience
    st.markdown("---")
    exercise_experience = st.text_area(
        "Previous exercise experience (optional)",
        value=st.session_state.user_data.get('exercise_experience', ''),
        placeholder="e.g., Played sports in college, did CrossFit for 2 years, yoga practitioner...",
        help="Tell us about your fitness background"
    )
    
    if nav_buttons():
        st.session_state.user_data.update({
            'activity_level': activity_level,
            'stress_level': stress_level,
            'sleep_hours': sleep_hours,
            'sleep_quality': sleep_quality,
            'fitness_level': fitness_level,
            'exercise_experience': exercise_experience
        })
        st.session_state.onboarding_step = 5
        st.rerun()

# ============ STEP 5: FITNESS ENVIRONMENT & CONSTRAINTS ============
elif st.session_state.onboarding_step == 5:
    st.title("🏠 Step 5: Fitness Environment & Constraints")
    show_progress()
    st.markdown("*Where and when will you train?*")
    
    # Workout Location
    st.markdown("### 📍 Workout Location")
    
    workout_location = st.selectbox(
        "Where will you primarily work out?*",
        ["Home", "Small Home Gym", "Large Gym/Fitness Center", "Outdoor", "Mixed (Various locations)"],
        index=0 if 'workout_location' not in st.session_state.user_data else
              ["Home", "Small Home Gym", "Large Gym/Fitness Center", "Outdoor", "Mixed (Various locations)"].index(
                  st.session_state.user_data.get('workout_location', 'Home')
              )
    )
    
    # Available Equipment
    st.markdown("---")
    st.markdown("### 🏋️ Available Equipment")
    
    equipment_options = [
        "None (Bodyweight only)",
        "Yoga Mat",
        "Resistance Bands",
        "Dumbbells",
        "Kettlebells",
        "Barbell & Plates",
        "Pull-up Bar",
        "Bench",
        "Squat Rack",
        "Cardio Machine (Treadmill/Bike)",
        "Full Gym Access"
    ]
    
    available_equipment = st.multiselect(
        "Select available equipment:",
        equipment_options,
        default=st.session_state.user_data.get('available_equipment', ["None (Bodyweight only)"])
    )
    
    # Workout Schedule
    st.markdown("---")
    st.markdown("### 📅 Workout Schedule")
    
    col1, col2 = st.columns(2)
    
    with col1:
        workout_frequency = st.selectbox(
            "How many days per week can you train?*",
            [2, 3, 4, 5, 6, 7],
            index=1 if 'workout_frequency' not in st.session_state.user_data else
                  [2, 3, 4, 5, 6, 7].index(st.session_state.user_data.get('workout_frequency', 3))
        )
    
    with col2:
        session_duration = st.selectbox(
            "How long per session?*",
            ["20-30 minutes", "30-45 minutes", "45-60 minutes", "60-90 minutes", "90+ minutes"],
            index=1 if 'session_duration' not in st.session_state.user_data else
                  ["20-30 minutes", "30-45 minutes", "45-60 minutes", "60-90 minutes", "90+ minutes"].index(
                      st.session_state.user_data.get('session_duration', '30-45 minutes')
                  )
        )
    
    # Preferred Days
    st.markdown("### 🗓️ Preferred Training Days")
    
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    selected_days = st.multiselect(
        "Select your preferred training days*",
        all_days,
        default=st.session_state.user_data.get('selected_days', all_days[:workout_frequency])
    )
    
    if len(selected_days) != workout_frequency:
        st.warning(f"⚠️ Please select exactly {workout_frequency} days")
    
    # Preferred Time
    preferred_time = st.selectbox(
        "Preferred workout time*",
        ["Morning (5-9 AM)", "Mid-Morning (9-12 PM)", "Afternoon (12-5 PM)", "Evening (5-9 PM)", "Night (9 PM+)", "Flexible"],
        index=0 if 'preferred_time' not in st.session_state.user_data else
              ["Morning (5-9 AM)", "Mid-Morning (9-12 PM)", "Afternoon (12-5 PM)", "Evening (5-9 PM)", "Night (9 PM+)", "Flexible"].index(
                  st.session_state.user_data.get('preferred_time', 'Morning (5-9 AM)')
              )
    )
    
    if nav_buttons():
        if len(selected_days) != workout_frequency:
            st.error(f"Please select exactly {workout_frequency} training days")
        else:
            st.session_state.user_data.update({
                'workout_location': workout_location,
                'available_equipment': available_equipment,
                'workout_frequency': workout_frequency,
                'session_duration': session_duration,
                'selected_days': selected_days,
                'preferred_time': preferred_time
            })
            st.session_state.onboarding_step = 6
            st.rerun()

# ============ STEP 6: FINAL REVIEW ============
elif st.session_state.onboarding_step == 6:
    st.title("✅ Step 6: Review Your Information")
    show_progress()
    st.markdown("*Please review your information before we generate your plan*")
    
    user_data = st.session_state.user_data
    
    # Personal Information
    with st.expander("👤 Personal Information", expanded=True):
        st.write(f"**Name:** {user_data.get('name')}")
        st.write(f"**Age:** {user_data.get('age')} years")
        st.write(f"**Gender:** {user_data.get('gender')}")
        st.write(f"**Height:** {user_data.get('height')} {'cm' if 'Metric' in user_data.get('unit_system') else 'inches'}")
        st.write(f"**Weight:** {user_data.get('weight')} {'kg' if 'Metric' in user_data.get('unit_system') else 'lbs'}")
        st.write(f"**BMI:** {user_data.get('bmi')} ({user_data.get('bmi_category')})")
    
    # Goals
    with st.expander("🎯 Goals & Target Areas", expanded=True):
        st.write(f"**Primary Goal:** {user_data.get('primary_goal')}")
        if user_data.get('secondary_goals'):
            st.write(f"**Secondary Goals:** {', '.join(user_data.get('secondary_goals'))}")
        st.write(f"**Target Areas:** {', '.join(user_data.get('target_areas', []))}")
    
    # Health Information
    with st.expander("🥼 Health & Medical Information", expanded=True):
        medical = user_data.get('medical_conditions', [])
        st.write(f"**Medical Conditions:** {', '.join(medical) if medical else 'None'}")
        st.write(f"**Taking Medications:** {user_data.get('taking_medications')}")
        if user_data.get('medications_list'):
            st.write(f"**Medications:** {user_data.get('medications_list')}")
        limitations = user_data.get('physical_limitations', '')
        st.write(f"**Physical Limitations:** {limitations if limitations else 'None reported'}")
    
    # Activity & Fitness
    with st.expander("📊 Activity & Fitness Level", expanded=True):
        st.write(f"**Activity Level:** {user_data.get('activity_level')}")
        st.write(f"**Stress Level:** {user_data.get('stress_level')}")
        st.write(f"**Sleep:** {user_data.get('sleep_hours')} hours/night ({user_data.get('sleep_quality')} quality)")
        st.write(f"**Fitness Level:** {user_data.get('fitness_level')}")
        if user_data.get('exercise_experience'):
            st.write(f"**Experience:** {user_data.get('exercise_experience')}")
    
    # Workout Setup
    with st.expander("🏋️ Fitness Environment & Schedule", expanded=True):
        st.write(f"**Location:** {user_data.get('workout_location')}")
        st.write(f"**Equipment:** {', '.join(user_data.get('available_equipment', []))}")
        st.write(f"**Frequency:** {user_data.get('workout_frequency')} days/week")
        st.write(f"**Session Duration:** {user_data.get('session_duration')}")
        st.write(f"**Training Days:** {', '.join(user_data.get('selected_days', []))}")
        st.write(f"**Preferred Time:** {user_data.get('preferred_time')}")
    
    st.markdown("---")
    st.info("💡 **Tip:** You can go back to edit any information using the '← Back' button")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("← Back to Edit", use_container_width=True):
            st.session_state.onboarding_step -= 1
            st.rerun()
    
    with col2:
        if st.button("✨ Generate My Plan", type="primary", use_container_width=True):
            st.session_state.onboarding_step = 7
            st.rerun()

# ============ STEP 7: GENERATE & DISPLAY PLAN ============
elif st.session_state.onboarding_step == 7:
    st.title("🎉 Your Personalized Fitness Plan")
    show_progress()
    
    # Generate plan if not already generated
    if 'fitness_plan' not in st.session_state:
        with st.spinner("🔮 Creating your personalized fitness plan..."):
            fitness_plan = fitness_advisor.generate_full_plan(st.session_state.user_data)
            st.session_state.fitness_plan = fitness_plan
    
    # Display the plan
    st.markdown(st.session_state.fitness_plan)
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Download Plan", use_container_width=True):
            st.download_button(
                label="Download as Text File",
                data=st.session_state.fitness_plan,
                file_name=f"FriskaAi_Plan_{st.session_state.user_data.get('name', 'User')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    with col2:
        if st.button("🔄 Start Over", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    with col3:
        if st.button("✏️ Modify Profile", use_container_width=True):
            st.session_state.onboarding_step = 1
            if 'fitness_plan' in st.session_state:
                del st.session_state['fitness_plan']
            st.rerun()
    
    # Feedback section
    st.markdown("---")
    st.markdown("### 💬 How do you like your plan?")
    
    feedback = st.text_area(
        "Share your feedback (optional)",
        placeholder="Let us know what you think about your personalized plan...",
        key="feedback_text"
    )
    
    if st.button("Submit Feedback", type="secondary"):
        st.success("Thank you for your feedback! 🙏")
    
    st.markdown("---")
    st.markdown("""
    ### 🚀 Next Steps
    1. **Save your plan** for easy reference
    2. **Start with Week 1** and focus on form
    3. **Track your progress** weekly
    4. **Listen to your body** and adjust as needed
    5. **Stay consistent** - results take time!
    
    ### 📞 Need Help?
    - Consult your doctor before starting any new exercise program
    - Work with a certified trainer for proper form guidance
    - Stop immediately if you experience sharp pain
    
    **Good luck on your fitness journey! 💪**
    """)
