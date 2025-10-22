import streamlit as st
import requests
import json
import os
import pandas as pd
from typing import Dict, List, Optional
import re
import random

# ---------------- CONFIG ----------------
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"

st.set_page_config(page_title="FriskaAi - Smart Fitness Advisor", layout="wide")

# ---------------- MEDICAL CONDITIONS LIST ----------------
MEDICAL_CONDITIONS = [
    "None", "Acanthosis Nigricans", "Addison's Disease", "Alzheimer's Disease", 
    "Ankylosing Spondylitis", "Anxiety Disorders", "Arrhythmias", "Asthma", 
    "Bipolar Disorder", "Bladder Cancer", "Brain Tumors", "Breast Cancer", 
    "Bronchitis", "Celiac Disease", "Cervical Cancer", "Cervical Spondylosis", 
    "Chickenpox", "Chikungunya", "Chronic Obstructive Pulmonary Disease (COPD)", 
    "Cirrhosis", "Colorectal Cancer", "Constipation", "Coronary Artery Disease (CAD)", 
    "COVID-19", "Cushing's Syndrome", "Deep Vein Thrombosis (DVT)", "Dementia", 
    "Dengue", "Depression", "Diabetic Ketoacidosis (DKA) Recovery", "Diarrheal Diseases", 
    "Disc Herniation", "Eating Disorders Recovery", "Encephalitis", "Epilepsy (Ketogenic Diet)", 
    "Fibromyalgia", "Fractures", "G6PD Deficiency", "Gallstones", 
    "Gastroesophageal Reflux Disease (GERD)", "Gastritis", "Glomerulonephritis", 
    "Gout", "Heart Failure", "Hepatitis", "Hepatitis E", "HIV/AIDS", "Hyperthyroidism", 
    "Hypertension", "Hypoglycemia", "Hypothyroidism", "Inflammatory Bowel Disease (Flare-up)", 
    "Inflammatory Bowel Disease (Remission)", "Influenza", "Insomnia", 
    "Interstitial Lung Disease", "Irritable Bowel Syndrome (IBS)", "Lactose Intolerance", 
    "Leukemia", "Low Back Pain", "Lung Cancer", "Lymphoma", "Malaria", "Measles", 
    "Meningitis", "Menopause", "Metabolic Syndrome", "Migraine", "Multiple Sclerosis", 
    "Myocardial Infarction (Heart Attack) Recovery", "Neuropathy", "Obesity", 
    "Obsessive Compulsive Disorder (OCD)", "Osteoarthritis", "Osteoporosis", 
    "Ovarian Cancer", "Pancreatic Cancer", "Parkinson's Disease", "Peptic Ulcer Disease", 
    "Perimenopause", "Peripheral Artery Disease", "Pneumonia", 
    "Polycystic Ovary Syndrome (PCOS)", "Post-Traumatic Stress Disorder (PTSD)", 
    "Prostate Cancer", "Prostate Enlargement (BPH)", "Pulmonary Embolism", 
    "Pulmonary Hypertension", "Pyelonephritis (Kidney Infection)", "Rheumatic Heart Disease", 
    "Rheumatoid Arthritis", "Schizophrenia", "Sexually Transmitted Infections (STIs)", 
    "Sickle Cell Disease", "Sleep Apnea", "Stevens-Johnson Syndrome (SJS) Recovery", 
    "Stomach Cancer", "Stroke Recovery", "Substance Use Disorder Recovery", 
    "Thalassemia", "Tuberculosis (TB)", "Type 1 Diabetes Mellitus", 
    "Type 2 Diabetes Mellitus", "Typhoid Fever", "Urinary Tract Infection (UTI)", 
    "Vitiligo", "Other"
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
        physical = (user_profile.get("physical_issues") or "").lower()
        
        high_risk = ["heart", "recent surgery", "stroke", "pulmonary embolism", "uncontrolled hypertension"]
        moderate_risk = ["diabetes", "arthritis", "osteoporosis", "obesity", "copd"]
        
        for hr in high_risk:
            if any(hr in m for m in medical) or hr in physical:
                return "High"
        for mr in moderate_risk:
            if any(mr in m for m in medical) or mr in physical:
                return "Moderate"
        
        return "Low" if medical and medical != ["none"] else "None"

    def classify_fitness_level(self, user_profile: Dict) -> str:
        """Auto-classify fitness level (Level 1-5)"""
        age = int(user_profile.get("age") or 0)
        activity = (user_profile.get("activity_level") or "").lower()
        risk = user_profile.get("risk_flag", "None")
        
        if risk == "High" or ("sedentary" in activity and age >= 75):
            return "Level 1 (Assisted/Low Function)"
        if ("sedentary" in activity and age >= 60) or ("light" in activity):
            return "Level 2 (Beginner Functional)"
        if "moderate" in activity:
            return "Level 3 (Moderate/Independent)"
        if "active" in activity and age < 60:
            return "Level 4 (Active Wellness)"
        return "Level 3 (Moderate/Independent)"

    def generate_exclude_tags(self, user_profile: Dict) -> List[str]:
        """Generate exercise exclusion tags"""
        tags = set()
        med = " ".join((user_profile.get("medical_conditions") or [])).lower()
        phys = (user_profile.get("physical_issues") or "").lower()
        
        if "back" in med or "back" in phys or "disc" in med:
            tags.add("avoid_spinal_flexion")
        if "hip" in phys or "knee" in phys or "fracture" in med:
            tags.add("avoid_high_impact")
        if "cardiac" in med or "heart" in med:
            tags.add("no_heavy_isometrics")
        
        return list(tags)

    def generate_day_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """Generate a single day's workout plan with reduced tokens"""
        name = user_profile.get("name", "there")
        fitness_level = user_profile.get("fitness_level", "Beginner")
        primary_goal = user_profile.get("primary_goal", "General fitness")
        location = user_profile.get("workout_location", "Home")
        
        prompt = f"""You are FriskaAI. Generate a concise workout plan for ONE day only.

**Day:** {day_name}
**User:** {name} ({fitness_level})
**Primary Goal:** {primary_goal}
**Location:** {location}

Format (STRICT):
### {day_name} - [Focus Area]

**Warm-up (5 min):**
- 2-3 exercises with duration

**Main Workout:**
For each exercise (4-5 exercises):
**Exercise Name**
- Benefit: [brief]
- Sets/Reps: [specific]
- Intensity: [RPE or %1RM]
- Rest: [time]
- Safety: [one tip]

**Cool-down (5 min):**
- 2-3 stretches

Keep response under 800 tokens. Be specific and actionable."""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "fitness-advisor",
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, a concise fitness coach."},
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
    total_steps = 10
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

# ============ STEP 1: BASIC IDENTITY ============
elif st.session_state.onboarding_step == 1:
    st.title("👤 Step 1: Basic Information")
    show_progress()
    st.markdown("*Tell us a bit about yourself*")
    
    name = st.text_input("What's your name?*", value=st.session_state.user_data.get('name', ''))
    age = st.number_input("Age*", 16, 100, st.session_state.user_data.get('age', 25))
    gender = st.selectbox("Gender*", ["Male", "Female", "Other"], 
                         index=["Male", "Female", "Other"].index(st.session_state.user_data.get('gender', 'Male')))
    
    if nav_buttons(show_back=False):
        if name:
            st.session_state.user_data.update({'name': name, 'age': age, 'gender': gender})
            st.session_state.onboarding_step = 2
            st.rerun()
        else:
            st.error("Please enter your name")

# ============ STEP 2: GOALS ============
elif st.session_state.onboarding_step == 2:
    st.title("🎯 Step 2: Your Goals")
    show_progress()
    st.markdown("*What do you want to achieve?*")
    
    primary_goal = st.selectbox("Choose ONE primary goal*", [
        "Mobility", "Balance", "Functional Strength", "Metabolic Health", 
        "Rehabilitation", "Reduce Pain", "Pre/Post-natal", "Posture Correction"
    ], index=0 if 'primary_goal' not in st.session_state.user_data else 
       ["Mobility", "Balance", "Functional Strength", "Metabolic Health", 
        "Rehabilitation", "Reduce Pain", "Pre/Post-natal", "Posture Correction"].index(
           st.session_state.user_data.get('primary_goal')))
    
    secondary_goals = st.multiselect("Secondary goals (optional, multiple):", [
        "Energy & Stamina", "Flexibility", "Stress Reduction", 
        "Healthy Habits", "Confidence & Quality of Life", "Weight Management"
    ], default=st.session_state.user_data.get('secondary_goals', []))
    
    doctor_clearance = "unknown"
    rehab_stage = None
    
    if primary_goal == "Rehabilitation":
        st.info("⚕️ Rehabilitation requires medical clearance")
        doctor_clearance = st.selectbox("Doctor clearance?*", 
            ["Unknown", "Yes - I have clearance", "No - Not yet cleared"])
        rehab_stage = st.selectbox("Rehab Stage*", 
            ["Phase 1 (Early/Acute)", "Phase 2 (Progressive)", "Phase 3 (Advanced)"])
    
    if nav_buttons():
        st.session_state.user_data.update({
            'primary_goal': primary_goal,
            'secondary_goals': secondary_goals,
            'doctor_clearance': doctor_clearance,
            'rehab_stage': rehab_stage
        })
        st.session_state.onboarding_step = 3
        st.rerun()

# ============ STEP 3: MEDICAL SCREENING ============
elif st.session_state.onboarding_step == 3:
    st.title("🏥 Step 3: Health & Medical Screening")
    show_progress()
    st.markdown("*This helps us create a safe program for you*")
    
    medical_conditions = st.multiselect(
        "Select any medical conditions (select all that apply)*", 
        MEDICAL_CONDITIONS[1:],
        default=st.session_state.user_data.get('medical_conditions', [])
    )
    
    if not medical_conditions:
        medical_conditions = ["None"]
    
    has_injuries = st.selectbox("Do you have any current injuries?", 
                               ["No", "Yes"],
                               index=0 if st.session_state.user_data.get('has_injuries', 'No') == 'No' else 1)
    
    injury_details = ""
    if has_injuries == "Yes":
        injury_bodypart = st.text_input("Body part affected", 
                                       value=st.session_state.user_data.get('injury_bodypart', ''))
        injury_severity = st.selectbox("Severity", ["Mild", "Moderate", "Severe"])
        injury_details = f"{injury_bodypart} ({injury_severity})"
    
    medications_affect = st.checkbox("I take medications that may affect exercise",
                                    value=st.session_state.user_data.get('medications_affect', False))
    
    doctor_clearance_general = "unknown"
    if st.session_state.user_data.get('primary_goal') != "Rehabilitation":
        doctor_clearance_general = st.selectbox(
            "Have you been cleared by a doctor for exercise?", 
            ["Unknown", "Yes", "No"]
        )
    
    # Risk assessment
    risk_flag = fitness_advisor.assess_risk_flag({
        "medical_conditions": medical_conditions,
        "physical_issues": injury_details,
        "medications_affect_exercise": medications_affect
    })
    
    # Continuation from Step 3 Medical Screening - Line 620
# Replace the incomplete line with:

    if risk_flag == "High" or (st.session_state.user_data.get('primary_goal') == "Rehabilitation" and doctor_clearance != "Yes - I have clearance"):
        st.error(f"⚠️ Risk Level: {risk_flag}")
        st.warning("""
        **Important:** Your health profile suggests you should consult with a healthcare provider before starting an exercise program.
        
        We recommend:
        - Speaking with your doctor or physiotherapist
        - Getting medical clearance for exercise
        - Working with a qualified fitness professional initially
        
        You may continue with the onboarding, but please seek professional guidance.
        """)
    elif risk_flag == "Moderate":
        st.info(f"⚡ Risk Level: {risk_flag} - We'll create a modified program for your safety")
    
    if nav_buttons():
        st.session_state.user_data.update({
            'medical_conditions': medical_conditions,
            'has_injuries': has_injuries,
            'injury_details': injury_details,
            'medications_affect': medications_affect,
            'doctor_clearance_general': doctor_clearance_general,
            'risk_flag': risk_flag
        })
        st.session_state.onboarding_step = 4
        st.rerun()

# ============ STEP 4: ACTIVITY & LIFESTYLE ============
elif st.session_state.onboarding_step == 4:
    st.title("🚶 Step 4: Activity & Lifestyle")
    show_progress()
    st.markdown("*Understanding your daily routine helps us create a realistic plan*")
    
    activity_level = st.select_slider(
        "Current Activity Level*",
        options=["Sedentary (Little/no exercise)", 
                 "Lightly Active (1-2 days/week)", 
                 "Moderately Active (3-4 days/week)", 
                 "Very Active (5-6 days/week)", 
                 "Extremely Active (Daily intense)"],
        value=st.session_state.user_data.get('activity_level', "Sedentary (Little/no exercise)")
    )
    
    sleep_quality = st.select_slider(
        "Sleep Quality*",
        options=["Poor (< 4 hours)", "Fair (4-6 hours)", "Good (6-8 hours)", "Excellent (8+ hours)"],
        value=st.session_state.user_data.get('sleep_quality', "Good (6-8 hours)")
    )
    
    stress_level = st.select_slider(
        "Daily Stress Level*",
        options=["Low", "Moderate", "High", "Very High"],
        value=st.session_state.user_data.get('stress_level', "Moderate")
    )
    
    occupation_type = st.selectbox(
        "Occupation Type*",
        ["Sedentary (Desk job)", "Light Physical", "Moderate Physical", "Heavy Physical", "Retired", "Student", "Other"],
        index=0 if 'occupation_type' not in st.session_state.user_data else 
              ["Sedentary (Desk job)", "Light Physical", "Moderate Physical", "Heavy Physical", "Retired", "Student", "Other"].index(
                  st.session_state.user_data.get('occupation_type'))
    )
    
    physical_issues = st.text_area(
        "Any physical limitations or issues? (optional)",
        value=st.session_state.user_data.get('physical_issues', ''),
        placeholder="e.g., Lower back stiffness, knee pain when climbing stairs, limited shoulder mobility..."
    )
    
    if nav_buttons():
        st.session_state.user_data.update({
            'activity_level': activity_level,
            'sleep_quality': sleep_quality,
            'stress_level': stress_level,
            'occupation_type': occupation_type,
            'physical_issues': physical_issues
        })
        st.session_state.onboarding_step = 5
        st.rerun()

# ============ STEP 5: PHYSICAL MEASUREMENTS ============
elif st.session_state.onboarding_step == 5:
    st.title("📏 Step 5: Physical Measurements")
    show_progress()
    st.markdown("*Optional but helps us track your progress*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        unit_system = st.radio(
            "Measurement System*",
            ["Metric (kg, cm)", "Imperial (lbs, inches)"],
            index=0 if st.session_state.user_data.get('unit_system', "Metric (kg, cm)") == "Metric (kg, cm)" else 1
        )
    
    with col2:
        st.write("")  # Spacer
    
    is_metric = "Metric" in unit_system
    
    col3, col4 = st.columns(2)
    
    with col3:
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
    
    with col4:
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
    
    st.markdown(f"""
    ### Your BMI: **{bmi}** (:{bmi_color}[{bmi_category}])
    *BMI is just one indicator and doesn't account for muscle mass or body composition*
    """)
    
    if nav_buttons():
        st.session_state.user_data.update({
            'unit_system': unit_system,
            'height': height,
            'weight': weight,
            'bmi': bmi,
            'bmi_category': bmi_category
        })
        st.session_state.onboarding_step = 6
        st.rerun()

# ============ STEP 6: WORKOUT SETUP ============
elif st.session_state.onboarding_step == 6:
    st.title("🏋️ Step 6: Workout Setup")
    show_progress()
    st.markdown("*Let's plan your training schedule*")
    
    workout_location = st.selectbox(
        "Where will you primarily work out?*",
        ["Home (Minimal Equipment)", "Home (Well-Equipped)", "Small Gym", "Large Gym/Fitness Center", "Outdoors", "Mixed"],
        index=0 if 'workout_location' not in st.session_state.user_data else 
              ["Home (Minimal Equipment)", "Home (Well-Equipped)", "Small Gym", "Large Gym/Fitness Center", "Outdoors", "Mixed"].index(
                  st.session_state.user_data.get('workout_location'))
    )
    
    st.markdown("**Available Equipment** *(select all that apply)*")
    equipment_options = [
        "None (Bodyweight only)", "Mat", "Resistance Bands", "Dumbbells", 
        "Kettlebells", "Barbell", "Squat Rack", "Bench", "Pull-up Bar",
        "TRX/Suspension Trainer", "Medicine Ball", "Foam Roller", "Stability Ball"
    ]
    
    available_equipment = st.multiselect(
        "Equipment:",
        equipment_options,
        default=st.session_state.user_data.get('available_equipment', ["Mat"])
    )
    
    if not available_equipment:
        available_equipment = ["None (Bodyweight only)"]
    
    workout_duration = st.select_slider(
        "Preferred workout duration per session*",
        options=["15-20 min", "20-30 min", "30-45 min", "45-60 min", "60+ min"],
        value=st.session_state.user_data.get('workout_duration', "30-45 min")
    )
    
    weekly_frequency = st.slider(
        "How many days per week can you commit?*",
        1, 7, 
        st.session_state.user_data.get('weekly_frequency', 3)
    )
    
    st.markdown("**Select specific workout days:***")
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    default_days = st.session_state.user_data.get('selected_days', [])
    if not default_days:
        # Auto-suggest based on frequency
        if weekly_frequency == 1:
            default_days = ["Wednesday"]
        elif weekly_frequency == 2:
            default_days = ["Monday", "Thursday"]
        elif weekly_frequency == 3:
            default_days = ["Monday", "Wednesday", "Friday"]
        elif weekly_frequency == 4:
            default_days = ["Monday", "Tuesday", "Thursday", "Friday"]
        elif weekly_frequency == 5:
            default_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        elif weekly_frequency == 6:
            default_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        else:
            default_days = days_of_week
    
    selected_days = st.multiselect(
        "Days:",
        days_of_week,
        default=default_days
    )
    
    if len(selected_days) != weekly_frequency:
        st.warning(f"⚠️ You selected {len(selected_days)} days but indicated {weekly_frequency} days per week. Please adjust.")
    
    if nav_buttons():
        if len(selected_days) > 0:
            st.session_state.user_data.update({
                'workout_location': workout_location,
                'available_equipment': available_equipment,
                'workout_duration': workout_duration,
                'weekly_frequency': weekly_frequency,
                'selected_days': selected_days
            })
            st.session_state.onboarding_step = 7
            st.rerun()
        else:
            st.error("Please select at least one workout day")

# ============ STEP 7: AUTO-CLASSIFICATION ============
elif st.session_state.onboarding_step == 7:
    st.title("📊 Step 7: Fitness Level Assessment")
    show_progress()
    st.markdown("*Based on your responses, we're determining your fitness level...*")
    
    # Auto-classify fitness level
    fitness_level = fitness_advisor.classify_fitness_level(st.session_state.user_data)
    
    # Generate exclusion tags
    exclude_tags = fitness_advisor.generate_exclude_tags(st.session_state.user_data)
    
    st.success(f"✅ **Your Fitness Level:** {fitness_level}")
    
    st.info("""
    **Fitness Level Definitions:**
    - **Level 1**: Assisted/Low Function - Focus on basic movements and daily activities
    - **Level 2**: Beginner Functional - Building foundation with simple exercises
    - **Level 3**: Moderate/Independent - Can perform standard exercises independently
    - **Level 4**: Active Wellness - Regular exerciser seeking optimization
    - **Level 5**: Athletic Performance - High-level training and performance goals
    """)
    
    if exclude_tags:
        st.warning(f"**Safety Modifications Applied:** {', '.join(exclude_tags)}")
    
    st.markdown("---")
    st.markdown("This assessment is based on:")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"- Age: {st.session_state.user_data.get('age')}")
        st.write(f"- Activity Level: {st.session_state.user_data.get('activity_level')}")
        st.write(f"- Risk Flag: {st.session_state.user_data.get('risk_flag', 'None')}")
    with col2:
        st.write(f"- Medical Conditions: {len(st.session_state.user_data.get('medical_conditions', []))}")
        st.write(f"- Primary Goal: {st.session_state.user_data.get('primary_goal')}")
    
    if nav_buttons(next_label="Continue to Target Areas →"):
        st.session_state.user_data.update({
            'fitness_level': fitness_level,
            'exclude_tags': exclude_tags
        })
        st.session_state.onboarding_step = 8
        st.rerun()

# ============ STEP 8: TARGET AREAS ============
elif st.session_state.onboarding_step == 8:
    st.title("🎯 Step 8: Target Areas")
    show_progress()
    st.markdown("*Which body areas do you want to focus on?*")
    
    st.markdown("**Select your primary focus areas** *(choose 1-3)*")
    
    target_options = [
        "Full Body", "Core", "Legs", "Arms", "Back", "Chest", 
        "Shoulders", "Glutes", "Stomach", "Cardio"
    ]
    
    target_areas = st.multiselect(
        "Target Areas:",
        target_options,
        default=st.session_state.user_data.get('target_areas', ["Full Body"])
    )
    
    if not target_areas:
        st.warning("Please select at least one target area")
    elif len(target_areas) > 3:
        st.info("💡 Tip: Focusing on 1-3 areas typically yields better results than spreading too thin")
    
    st.markdown("---")
    st.markdown("### 📝 Optional: Specific Focus")
    
    problem_areas = st.text_area(
        "Any specific problem areas or concerns?",
        value=st.session_state.user_data.get('problem_areas', ''),
        placeholder="e.g., Love handles, weak lower back, tight hamstrings, improving posture..."
    )
    
    if nav_buttons():
        if target_areas:
            st.session_state.user_data.update({
                'target_areas': target_areas,
                'problem_areas': problem_areas
            })
            st.session_state.onboarding_step = 9
            st.rerun()
        else:
            st.error("Please select at least one target area")

# ============ STEP 9: FINAL REVIEW ============
elif st.session_state.onboarding_step == 9:
    st.title("📋 Step 9: Review Your Profile")
    show_progress()
    st.markdown("*Please review your information before we generate your plan*")
    
    data = st.session_state.user_data
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Personal Info")
        st.write(f"**Name:** {data.get('name')}")
        st.write(f"**Age:** {data.get('age')}")
        st.write(f"**Gender:** {data.get('gender')}")
        
        st.markdown("### 🎯 Goals")
        st.write(f"**Primary:** {data.get('primary_goal')}")
        if data.get('secondary_goals'):
            st.write(f"**Secondary:** {', '.join(data.get('secondary_goals', []))}")
        
        st.markdown("### 📏 Measurements")
        st.write(f"**Height:** {data.get('height')} {'cm' if 'Metric' in data.get('unit_system', '') else 'inches'}")
        st.write(f"**Weight:** {data.get('weight')} {'kg' if 'Metric' in data.get('unit_system', '') else 'lbs'}")
        st.write(f"**BMI:** {data.get('bmi')} ({data.get('bmi_category')})")
        
        st.markdown("### 🏋️ Workout Setup")
        st.write(f"**Location:** {data.get('workout_location')}")
        st.write(f"**Duration:** {data.get('workout_duration')}")
        st.write(f"**Frequency:** {data.get('weekly_frequency')} days/week")
        st.write(f"**Days:** {', '.join(data.get('selected_days', []))}")
    
    with col2:
        st.markdown("### 🏥 Health Profile")
        medical = data.get('medical_conditions', [])
        if medical == ["None"] or not medical:
            st.write("**Conditions:** None reported")
        else:
            st.write(f"**Conditions:** {len(medical)} condition(s)")
            for cond in medical[:3]:
                st.write(f"  - {cond}")
            if len(medical) > 3:
                st.write(f"  - *...and {len(medical) - 3} more*")
        
        st.write(f"**Risk Level:** {data.get('risk_flag', 'None')}")
        st.write(f"**Injuries:** {data.get('has_injuries', 'No')}")
        
        st.markdown("### 🚶 Activity Level")
        st.write(f"**Current Activity:** {data.get('activity_level', '').split('(')[0]}")
        st.write(f"**Sleep:** {data.get('sleep_quality', '').split('(')[0]}")
        st.write(f"**Stress:** {data.get('stress_level')}")
        st.write(f"**Occupation:** {data.get('occupation_type')}")
        
        st.markdown("### 🎯 Focus Areas")
        st.write(f"**Target Areas:** {', '.join(data.get('target_areas', []))}")
        st.write(f"**Fitness Level:** {data.get('fitness_level')}")
        
        st.markdown("### 🔧 Equipment")
        equipment = data.get('available_equipment', [])
        if len(equipment) <= 3:
            st.write(f"**Available:** {', '.join(equipment)}")
        else:
            st.write(f"**Available:** {', '.join(equipment[:3])}, +{len(equipment)-3} more")
    
    st.markdown("---")
    
    col_edit, col_generate = st.columns([1, 2])
    
    with col_edit:
        if st.button("✏️ Edit Profile", use_container_width=True):
            st.session_state.onboarding_step = 1
            st.rerun()
    
    with col_generate:
        if st.button("✨ Generate My Fitness Plan!", type="primary", use_container_width=True):
            st.session_state.onboarding_step = 10
            st.rerun()

# ============ STEP 10: GENERATE & DISPLAY PLAN ============
elif st.session_state.onboarding_step == 10:
    st.title("🎉 Your Personalized Fitness Plan")
    st.markdown("---")
    
    # Generate the plan
    if 'generated_plan' not in st.session_state:
        with st.spinner("🔧 Creating your personalized fitness plan... This may take a moment..."):
            try:
                plan = fitness_advisor.generate_full_plan(st.session_state.user_data)
                st.session_state.generated_plan = plan
            except Exception as e:
                st.error(f"❌ Error generating plan: {e}")
                st.session_state.generated_plan = "Error generating plan. Please try again."
    
    # Display the plan
    st.markdown(st.session_state.generated_plan)
    
    st.markdown("---")
    
    # Exercise demos section
    st.markdown("## 🎥 Exercise Demonstrations")
    
    exercise_db = fitness_advisor.exercise_db
    user_target_areas = st.session_state.user_data.get('target_areas', ['Full Body'])
    
    # Get relevant exercises
    relevant_exercises = exercise_db.get_exercises_by_target_area(
        user_target_areas, 
        st.session_state.user_data.get('workout_location', 'Home')
    )
    
    # Filter by equipment
    relevant_exercises = {
        k: v for k, v in relevant_exercises.items()
        if k in exercise_db.get_exercises_by_equipment(
            st.session_state.user_data.get('available_equipment', []),
            st.session_state.user_data.get('workout_location', 'Home')
        )
    }
    
    # Filter out contraindicated exercises
    medical_conditions = st.session_state.user_data.get('medical_conditions', ['None'])
    safe_exercises = {
        k: v for k, v in relevant_exercises.items()
        if not exercise_db.is_contraindicated(v, medical_conditions)
    }
    
    if safe_exercises:
        st.info(f"💡 Here are {len(safe_exercises)} recommended exercises for your program:")
        
        # Display exercises in expandable sections
        for key, exercise in list(safe_exercises.items())[:6]:  # Show top 6
            with st.expander(f"**{exercise['name']}** - {exercise['type']} ({exercise['level']})"):
                col_info, col_video = st.columns([2, 1])
                
                with col_info:
                    st.markdown(f"**✅ Benefits:** {exercise['benefits']}")
                    st.markdown(f"**💪 Sets/Reps:** {exercise['reps']}")
                    st.markdown(f"**🔥 Intensity:** {exercise['intensity']}")
                    st.markdown(f"**⏳ Rest:** {exercise['rest']}")
                    st.markdown(f"**⚠️ Safety:** {exercise['safety']}")
                    
                    st.markdown("**Steps:**")
                    for i, step in enumerate(exercise.get('steps', []), 1):
                        st.write(f"{i}. {step}")
                    
                    if exercise.get('common_mistakes'):
                        st.markdown("**❌ Common Mistakes to Avoid:**")
                        for mistake in exercise['common_mistakes']:
                            st.write(f"- {mistake}")
                
                with col_video:
                    # Try to display video/GIF if available
                    video_path = f"archive/exercisedb_v1_sample/gifs_360x360/{exercise.get('demo_video', '')}"
                    if os.path.exists(video_path):
                        st.video(video_path)
                    else:
                        st.info("🎬 Demo video coming soon")
                    
                    st.markdown(f"**⚙️ Equipment:**")
                    for equip in exercise.get('equipment', []):
                        st.write(f"- {equip}")
                    
                    st.markdown(f"**⭐ Rating:** {exercise.get('rating', 'N/A')}/5.0")
    else:
        st.warning("No specific exercise demos available for your current setup.")
    
    st.markdown("---")
    
    # Download and action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Download as text file
        plan_text = st.session_state.generated_plan
        st.download_button(
            label="📥 Download Plan (TXT)",
            data=plan_text,
            file_name=f"FriskaAi_Plan_{st.session_state.user_data.get('name', 'User')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        if st.button("🔄 Generate New Plan", use_container_width=True):
            if 'generated_plan' in st.session_state:
                del st.session_state.generated_plan
            st.rerun()
    
    with col3:
        if st.button("🚀 Start Over", type="secondary", use_container_width=True):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.onboarding_step = 0
            st.rerun()
    
    st.markdown("---")
    
    # Footer
    st.markdown("""
    ### 💡 Tips for Success
    
    1. **Consistency is Key**: Stick to your scheduled days
    2. **Listen to Your Body**: Rest when needed, push when able
    3. **Track Progress**: Keep a workout journal
    4. **Stay Hydrated**: Drink water before, during, and after
    5. **Warm-up & Cool-down**: Never skip these crucial steps
    
    ### ⚠️ Important Reminders
    
    - Stop immediately if you experience sharp pain
    - Consult your healthcare provider with any concerns
    - Modify exercises as needed for your comfort
    - Progress gradually - don't rush
    
    ### 📞 Need Help?
    
    If you have questions about any exercise or need modifications, consult with a qualified fitness professional.
    
    ---
    
    **FriskaAi** - Your Personal Fitness Advisor | Created with ❤️ for your health journey
    """)    