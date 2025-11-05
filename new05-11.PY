import streamlit as st
import requests
import json
import os
import pandas as pd
from typing import Dict, List, Optional
import re
import random


condition_data = pd.read_excel("Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx")
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
        """Return full Excel-based instructions for each condition selected."""
        guidelines = []
        for cond in medical_conditions:
            matches = condition_data[condition_data["Condition"].str.contains(cond, case=False, na=False)]
            for _, row in matches.iterrows():
                guidelines.append(
                    f"🩺 Condition: {row['Condition']}\n"
                    f"- Contraindicated Exercises: {row['Contraindicated Exercises']}\n"
                    f"- Modified / Safer Exercises: {row['Modified / Safer Exercises']}\n"
                    f"- Exercise Type: {row['Exercise Type']}\n"
                    f"- Affected Body Region: {row['Affected Body Region']}\n"
                    f"- Intensity Limit: {row['Intensity Limit']}\n"
                )
        if not guidelines:
            return "No condition-specific restrictions or modifications."
        return "\n".join(guidelines)


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
        """Generate one day's plan using full Excel condition data and fitness-level adaptation."""
        name = user_profile.get("name", "User")
        fitness_level = user_profile.get("fitness_level", "Level 3 - Intermediate")
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        location = user_profile.get("workout_location", "Home")
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        target_areas = user_profile.get("target_areas", ["Full Body"])

        # 🩺 Include full Excel-based condition guide
        condition_guidelines = self.get_condition_guidelines(medical_conditions)

        # 🎯 Determine daily focus area
        focus = target_areas[day_index % len(target_areas)]

        # 🧘 Fitness-level guidance
        if "Beginner" in fitness_level or "Level 1" in fitness_level or "Level 2" in fitness_level:
            intensity_instruction = (
                "For BEGINNERS: Avoid heavy lifts, high-impact moves, or long holds. "
                "Use bodyweight, light resistance, and focus on slow, controlled form."
            )
        elif "Intermediate" in fitness_level or "Level 3" in fitness_level:
            intensity_instruction = (
                "For INTERMEDIATE users: Moderate intensity allowed. Combine strength and mobility "
                "while maintaining good form and breathing."
            )
        else:
            intensity_instruction = (
                "For ADVANCED users: Include progressive overload, compound movements, and moderate-high intensity as appropriate."
            )

        # 🧠 Build the full instruction prompt
        prompt = f"""
    
You are FriskaAI, a certified clinical exercise physiologist and fitness program designer. Your job is to generate medically safe, goal-based workout plans.

### USER PROFILE
Name: {name}
Age: {user_profile.get('age')}
Goal: {primary_goal}
Experience Level: {fitness_level} (Beginner/Intermediate/Advanced only)
Training Days: {", ".join(user_profile.get("training_days", []))}
Location: {location}
Medical Conditions: {", ".join(medical_conditions)}
Focus Today: {focus}

### MEDICAL RULES (STRICT)
Use the following condition-specific restrictions and safe exercise recommendations:
{condition_guidelines}

- ONLY apply medical modification rules if the user has a medical condition.
- If NO medical condition: follow age-appropriate fitness progression instead of general population rules.


### GENERAL TRAINING RULES
- If age < 40 and no mobility issues → **NO seated/chair workouts**
- Warm-ups should be **mobility + activation**, not strength exercises
- Cool-downs should be **stretching + breathing**, not main exercises
- Every day MUST have different exercises (no repeating the same plan)
- Ensure push / pull / legs / core movement balance
- Prioritize functional standing movements unless medically restricted
### GENERAL TRAINING RULES
- Prioritize safety, joint protection, and controlled tempo
- Warm-ups must be mobility + activation (not strength drills)
- Cool-downs must be stretching + breathing (not main exercises)
- No repetition of warm-up/cool-down movements in main workout
- Maintain balance between push / pull / legs / core

### AGE-ADAPTIVE TRAINING RULES (STRICT)
If Age ≥ 60:
- Treat as beginner unless user explicitly states very active
- Use low-impact, joint-friendly movements
- Prioritize: sit-to-stand, wall push-ups, band rows, heel raises, step taps, marching, supported balance work
- Avoid for first 4 weeks:
  - Jumping or impact work (NO jumping jacks / jump squats)
  - Floor planks (use standing/bench supported core instead)
  - Heavy squats (use chair-assisted sit-to-stand)
  - Burpees, mountain climbers, HIIT moves
- Balance and fall-prevention must be included weekly
- Mobility before stability before strength progression

### AGE < 60 RULE
If age < 60 and no limitations → avoid seated or chair-based exercises unless goal is rehab

### NO CONDITION RULE UPDATE
If user has NO medical condition:
- Still follow age-appropriate exercise safety rules
- Senior guidelines override fitness level when needed
- Focus on foundational strength, mobility & balance

### INTENSITY RULES
Beginner = 
- Bodyweight + bands 
- 2–3 sets × 8–12 reps
- RPE 5–7
- Slow tempo & controlled breathing

Intermediate =
- Progressive overload allowed
- Dumbbells/bands ok
- RPE 6–8

Advanced =
- Higher volume & load
- Complex patterns allowed only if safe

### EQUIPMENT RULES
Home workout movement priority:
1. Bodyweight
2. Resistance band
3. Dumbbell (if user has)

### WORKOUT FORMAT (STRICT)
Format exactly as follows:

### {day_name} – {focus}

**Warm-Up (5 minutes)**
Warm-up must not include squats, planks, or strength movements. Only mobility:
Examples: marching in place, shoulder circles, ankle mobility, thoracic rotations, hip openers, diaphragmatic breathing
- 3 movements  
Format each:  
Movement – Benefit – Duration – Safety cue  
(Examples: arm circles, marching in place, hip openers, cat-cow, ankle mobilizations, breathing drills)

**Main Workout (4–6 exercises)**  
For each exercise:  
Exercise Name  
- Benefit
- Steps/How to do?  
- Sets x Reps  
- RPE/Intensity  
- Rest  
- Safety cue

Rules:  
- Must match user goal & fitness level  
- Must follow medical sheet when condition exists  
- Must alternate muscle groups if possible  

**Cool-Down (5 minutes)** 
Cool-down must not include yoga poses requiring hands/knees on floor unless user is under 60 and mobile.
- 3 movements  
Format each:  
Stretch / breathing drill – Benefit – Duration – Safety cue

### IMPORTANT SAFETY REQUIREMENTS
- NO seated/rehab-style movements unless medically required  
- NO repeating same day workout  
- Warm-ups = mobility/activation only  
- Cool-downs = stretching + breathing only  
- If condition has contraindicated exercises → strictly avoid  
- Prefer approved/safe exercises from Excel sheet  

Generate the workout ONLY. No motivational text, no duplication.
"""


        # --- Send to API ---
        try:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": "fitness-advisor",
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, a concise medical fitness expert."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1200,
            }
            resp = requests.post(self.endpoint_url, headers=headers, json=payload, timeout=40)
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

        # fallback
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
if 'fitness_plan' not in st.session_state:
    st.session_state.fitness_plan = None

# ============ MAIN SINGLE PAGE FORM ============
st.title("🏋️‍♂️ FriskaAi - Your Personal Fitness Advisor")
st.markdown("**Personalized health & function plan for special populations.**")
st.markdown("---")

with st.form("fitness_intake_form"):
    
    # ============ SECTION 1: BASIC INFORMATION ============
    st.header("👤 Basic Information & Measurements")
    
    name = st.text_input("What's your name?*")
    
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age*", 16, 100, 25)
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
    
    # Calculate BMI
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
    
    # ============ SECTION 2: GOALS & TARGET AREAS ============
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
        "Energy & Stamina",
        "Flexibility",
        "Stress Reduction",
        "Healthy Habits",
        "Confidence & Quality of Life",
        "Weight Management"
    ]
    
    secondary_goals = st.multiselect("Secondary goals (optional):", secondary_goal_options)
    
    target_options = [
        "Full Body", "Core", "Legs", "Arms", "Back", "Chest", 
        "Shoulders", "Glutes", "Stomach"
    ]
    
    target_areas = st.multiselect("Target Areas (1-3)*:", target_options, default=["Full Body"])
    
    doctor_clearance = "Unknown"
    rehab_stage = None
    if "Rehabilitation" in primary_goal:
        st.info("⚕️ Rehabilitation requires medical clearance")
        doctor_clearance = st.selectbox("Doctor clearance?*", 
            ["Unknown", "Yes - I have clearance", "No - Not yet cleared"])
        if doctor_clearance == "Yes - I have clearance":
            rehab_stage = st.selectbox("Rehab Stage*", 
                ["Phase 1 (Early/Acute)", "Phase 2 (Progressive)", "Phase 3 (Advanced)"])
    
    st.markdown("---")
    
    # ============ SECTION 3: HEALTH & MEDICAL SCREENING
    # ============ SECTION 3: HEALTH & MEDICAL SCREENING ============
    st.header("🏥 Health & Medical Screening")
    
    st.warning("⚠️ Please consult your healthcare provider before starting any new exercise program, especially if you have medical conditions.")
    
    medical_conditions = st.multiselect(
        "Do you have any of these medical conditions?*",
        MEDICAL_CONDITIONS,
        default=["None"]
    )
    
    medical_other = ""
    if "Other" in medical_conditions:
        medical_other = st.text_input("Please specify other medical condition(s)*")
    
    st.subheader("💊 Current Medications")
    takes_medication = st.radio("Are you currently taking any medications?*", ["No", "Yes"])
    
    medication_list = ""
    if takes_medication == "Yes":
        medication_list = st.text_area(
            "Please list your medications (one per line):",
            placeholder="e.g., Blood pressure medication\nDiabetes medication\nThyroid medication"
        )
    
    physical_limitations = st.text_area(
        "Do you have any physical limitations or injuries?",
        placeholder="e.g., Recent knee surgery, chronic back pain, limited shoulder mobility..."
    )
    
    st.markdown("---")
    
    # ============ SECTION 4: ACTIVITY & LIFESTYLE ASSESSMENT ============
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
        stress_level = st.selectbox(
            "Daily Stress Level*",
            ["Low", "Moderate", "High", "Very High"]
        )
    
    with col8:
        sleep_quality = st.selectbox(
            "Sleep Quality*",
            ["Poor", "Fair", "Good", "Excellent"]
        )
    
    sleep_hours = st.slider("Average Sleep Hours per Night*", 3, 12, 7, 1)
    
    st.subheader("💪 Fitness Experience")
    
    fitness_level_options = [
        "Level 1 - Complete Beginner (New to exercise)",
        "Level 2 - Beginner (Some experience, 0-6 months)",
        "Level 3 - Intermediate (Regular exerciser, 6 months - 2 years)",
        "Level 4 - Advanced (Experienced, 2+ years consistent training)",
        "Level 5 - Expert (Athlete or fitness professional)"
    ]
    
    fitness_level = st.selectbox("Fitness Level*", fitness_level_options)
    
    previous_experience = st.text_area(
        "Previous Exercise Experience (optional)",
        placeholder="e.g., Played soccer in high school, did yoga for 2 years, completed a 5K race..."
    )
    
    st.markdown("---")
    
    # ============ SECTION 5: FITNESS ENVIRONMENT & CONSTRAINTS ============
    st.header("🏠 Fitness Environment & Constraints")
    
    workout_location_options = [
        "Home",
        "Small Home Gym",
        "Large Commercial Gym",
        "Outdoor/Park",
        "Mixed (Home + Gym)"
    ]
    
    workout_location = st.selectbox("Primary Workout Location*", workout_location_options)
    
    equipment_options = [
        "None - Bodyweight Only",
        "Mat",
        "Resistance Bands",
        "Dumbbells",
        "Kettlebells",
        "Barbell",
        "Pull-up Bar",
        "Bench",
        "Squat Rack",
        "Treadmill",
        "Stationary Bike",
        "Rowing Machine",
        "Medicine Ball",
        "Foam Roller",
        "TRX/Suspension Trainer"
    ]
    
    available_equipment = st.multiselect(
        "Available Equipment*",
        equipment_options,
        default=["None - Bodyweight Only"]
    )
    
    st.subheader("📅 Training Schedule")
    
    col9, col10 = st.columns(2)
    with col9:
        days_per_week = st.selectbox(
            "Workout Frequency (days per week)*",
            [1, 2, 3, 4, 5, 6, 7],
            index=2
        )
    
    with col10:
        session_duration_options = [
            "15-20 minutes",
            "20-30 minutes",
            "30-45 minutes",
            "45-60 minutes",
            "60-90 minutes",
            "90+ minutes"
        ]
        session_duration = st.selectbox("Preferred Session Duration*", session_duration_options, index=2)
    
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    selected_days = st.multiselect(
        f"Preferred Training Days* (Select {days_per_week})",
        all_days,
        default=all_days[:days_per_week]
    )
    
    preferred_time_options = [
        "Early Morning (5-7 AM)",
        "Morning (7-10 AM)",
        "Late Morning (10 AM-12 PM)",
        "Afternoon (12-3 PM)",
        "Late Afternoon (3-6 PM)",
        "Evening (6-9 PM)",
        "Night (9 PM+)",
        "Flexible/Varies"
    ]
    
    preferred_time = st.selectbox("Preferred Workout Time*", preferred_time_options)
    
    st.markdown("---")
    
    # ============ FORM SUBMISSION ============
    submitted = st.form_submit_button("✨ Generate My Personalized Plan", use_container_width=True)
    
    if submitted:
        # Validate required fields
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
            for error in validation_errors:
                st.error(error)
        else:
            # Build user profile dictionary
            final_medical_conditions = medical_conditions.copy()
            if "Other" in final_medical_conditions and medical_other:
                final_medical_conditions.remove("Other")
                final_medical_conditions.append(medical_other)
            
            final_primary_goal = primary_goal_other if primary_goal == "Other" else primary_goal
            
            user_profile = {
                # Basic Info
                "name": name,
                "age": age,
                "gender": gender,
                "height": height,
                "weight": weight,
                "unit_system": unit_system,
                "bmi": bmi,
                "bmi_category": bmi_category,
                
                # Goals
                "primary_goal": final_primary_goal,
                "secondary_goals": secondary_goals,
                "target_areas": target_areas,
                "doctor_clearance": doctor_clearance,
                "rehab_stage": rehab_stage,
                
                # Health
                "medical_conditions": final_medical_conditions,
                "takes_medication": takes_medication,
                "medication_list": medication_list,
                "physical_limitations": physical_limitations,
                
                # Activity
                "current_activity": current_activity,
                "stress_level": stress_level,
                "sleep_hours": sleep_hours,
                "sleep_quality": sleep_quality,
                "fitness_level": fitness_level,
                "previous_experience": previous_experience,
                
                # Environment
                "workout_location": workout_location,
                "available_equipment": available_equipment,
                "days_per_week": days_per_week,
                "session_duration": session_duration,
                "selected_days": selected_days,
                "training_days": selected_days,  # alias for compatibility
                "preferred_time": preferred_time
            }
            
            # Generate plan
            with st.spinner("🎯 Analyzing your profile and generating your personalized fitness plan..."):
                st.session_state.fitness_plan = fitness_advisor.generate_full_plan(user_profile)
                st.session_state.user_profile = user_profile

# ============ DISPLAY GENERATED PLAN ============
if st.session_state.fitness_plan:
    st.success("✅ Your personalized fitness plan is ready!")
    
    st.markdown("---")
    
    # Display the plan
    st.markdown(st.session_state.fitness_plan)
    
    st.markdown("---")
    
    # Action buttons
    col_actions = st.columns([1, 1, 1, 2])
    
    with col_actions[0]:
        # Download button
        plan_text = st.session_state.fitness_plan
        st.download_button(
            label="📥 Download Plan",
            data=plan_text,
            file_name=f"FriskaAi_Plan_{st.session_state.user_profile['name']}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col_actions[1]:
        # Start over button
        if st.button("🔄 Create New Plan", use_container_width=True):
            st.session_state.fitness_plan = None
            st.session_state.user_profile = None
            st.rerun()
    
    with col_actions[2]:
        # Print button (opens print dialog)
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
    
    # Feedback section
    st.header("💬 Feedback")
    st.markdown("**How satisfied are you with your personalized plan?**")
    
    feedback_cols = st.columns(5)
    feedback_emoji = ["😞", "😐", "🙂", "😊", "🤩"]
    feedback_text = ["Very Unsatisfied", "Unsatisfied", "Neutral", "Satisfied", "Very Satisfied"]
    
    for i, (col, emoji, text) in enumerate(zip(feedback_cols, feedback_emoji, feedback_text)):
        with col:
            if st.button(f"{emoji}\n{text}", key=f"feedback_{i}", use_container_width=True):
                st.success(f"Thank you for your feedback! You rated: {text}")
    
    feedback_comments = st.text_area(
        "Additional comments or suggestions (optional):",
        placeholder="Tell us what you think about the plan..."
    )
    
    if st.button("Submit Feedback"):
        if feedback_comments:
            st.success("✅ Thank you for your feedback! We appreciate your input.")
        else:
            st.info("Feedback submitted!")
    
    st.markdown("---")
    
    # Safety reminder
    st.info("""
    ### ⚠️ Important Safety Reminders
    - Always consult with your healthcare provider before starting a new exercise program
    - Stop immediately if you experience pain, dizziness, or unusual discomfort
    - Stay hydrated and listen to your body
    - If you have medical conditions, follow your doctor's recommendations
    - Progress gradually and don't rush
    """)
    
    # Disclaimer
    st.markdown("---")
    st.caption("""
    **Disclaimer:** This fitness plan is generated based on the information you provided and is for informational purposes only. 
    It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician 
    or other qualified health provider with any questions you may have regarding a medical condition or exercise program.
    """)

else:
    # Show welcome message when no plan is generated
    st.markdown("---")
    st.info("👆 Please fill out the form above to generate your personalized fitness plan!")
    
    # Show some benefits
    st.markdown("### 🌟 What You'll Get:")
    benefit_cols = st.columns(3)
    
    with benefit_cols[0]:
        st.markdown("""
        **🎯 Personalized Plan**
        - Tailored to your goals
        - Adapted to your fitness level
        - Safe for your conditions
        """)
    
    with benefit_cols[1]:
        st.markdown("""
        **📅 Structured Schedule**
        - Day-by-day workouts
        - Progressive training
        - Flexible timing
        """)
    
    with benefit_cols[2]:
        st.markdown("""
        **🏥 Medical Safety**
        - Condition-specific adaptations
        - Safe exercise selection
        - Professional guidance
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p><strong>FriskaAi - Smart Fitness Advisor</strong></p>
    <p>Powered by AI | Designed for Your Health & Wellness</p>
    <p>© 2025 FriskaAi. All rights reserved.</p>
</div>
""", unsafe_allow_html=True)
