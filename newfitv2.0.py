import streamlit as st
import requests
from typing import Dict, List, Optional
import re
from datetime import datetime

# ============ CONFIGURATION ============
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"

st.set_page_config(
    page_title="FriskaAI Fitness Coach",
    page_icon="💪",
    layout="wide"
)

# ============ MEDICAL CONDITIONS DATABASE ============
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

# ============ CONDITION-SPECIFIC GUIDELINES ============
CONDITION_GUIDELINES = {
    "Hypertension": {
        "contraindicated": ["Heavy isometric exercises", "Valsalva maneuver exercises", "High-intensity interval training without clearance"],
        "recommended": ["Moderate aerobic exercise", "Light resistance training", "Yoga", "Walking"],
        "intensity_limit": "RPE 5-7 (moderate)",
        "special_notes": "Monitor blood pressure before and after exercise. Avoid breath-holding during lifts."
    },
    "Type 2 Diabetes": {
        "contraindicated": ["Exercises causing blood sugar spikes", "Long fasting cardio"],
        "recommended": ["Resistance training 2-3x/week", "Moderate cardio", "Post-meal walks"],
        "intensity_limit": "RPE 5-8",
        "special_notes": "Check blood glucose before/after exercise. Keep snacks available."
    },
    "Osteoarthritis": {
        "contraindicated": ["High-impact jumping", "Deep squats", "Running on hard surfaces"],
        "recommended": ["Swimming", "Cycling", "Resistance bands", "Range of motion exercises"],
        "intensity_limit": "RPE 4-6 (low to moderate)",
        "special_notes": "Warm up thoroughly. Use joint-friendly modifications."
    },
    "Chronic Lower Back Pain": {
        "contraindicated": ["Heavy deadlifts", "Loaded spinal flexion", "Twisting under load"],
        "recommended": ["Core stability exercises", "Hip hinges", "Bird dogs", "Dead bugs"],
        "intensity_limit": "RPE 4-6",
        "special_notes": "Maintain neutral spine. Progress gradually."
    },
    "Osteoporosis": {
        "contraindicated": ["Forward flexion", "Twisting", "High-impact activities"],
        "recommended": ["Weight-bearing exercises", "Resistance training", "Balance training"],
        "intensity_limit": "RPE 5-7",
        "special_notes": "Focus on bone-loading exercises. Avoid fall risk."
    },
    "Asthma": {
        "contraindicated": ["Cold air exposure", "Continuous high-intensity cardio"],
        "recommended": ["Interval training", "Swimming", "Yoga", "Controlled breathing exercises"],
        "intensity_limit": "RPE 5-7",
        "special_notes": "Keep inhaler accessible. Warm up gradually."
    }
}

# ============ FITNESS ADVISOR CLASS ============
class FitnessAdvisor:
    """Core fitness planning engine with medical safety protocols"""
    
    def __init__(self, api_key: str, endpoint_url: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
    
    def _build_system_prompt(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        is_modification: bool = False,
        modification_request: str = ""
    ) -> str:
        """
        Build highly structured, deterministic system prompt for workout generation.
        Inspired by the meal plan prompt architecture for maximum accuracy.
        """
        
        # Extract profile data
        name = user_profile.get("name", "User")
        age = user_profile.get("age", 30)
        gender = user_profile.get("gender", "Other")
        fitness_level = user_profile.get("fitness_level", "Level 3 - Intermediate")
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        location = user_profile.get("workout_location", "Home")
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        target_areas = user_profile.get("target_areas", ["Full Body"])
        session_duration = user_profile.get("session_duration", "30-45 minutes")
        available_equipment = user_profile.get("available_equipment", ["None - Bodyweight Only"])
        physical_limitations = user_profile.get("physical_limitations", "")
        
        # Determine focus for the day
        focus = target_areas[day_index % len(target_areas)]
        
        # Build condition-specific guidelines
        condition_rules = self._build_condition_rules(medical_conditions)
        
        # Determine fitness level category
        if "Level 1" in fitness_level or "Level 2" in fitness_level or "Beginner" in fitness_level:
            level_category = "Beginner"
            intensity_range = "RPE 4-6"
            sets_range = "2-3 sets"
            reps_range = "8-12 reps"
        elif "Level 3" in fitness_level or "Intermediate" in fitness_level:
            level_category = "Intermediate"
            intensity_range = "RPE 6-8"
            sets_range = "3-4 sets"
            reps_range = "8-15 reps"
        else:
            level_category = "Advanced"
            intensity_range = "RPE 7-9"
            sets_range = "4-5 sets"
            reps_range = "6-12 reps"
        
        # Age-based adaptations
        age_adaptations = self._get_age_adaptations(age, medical_conditions)
        
        prompt = f"""You are FriskaAI, a certified clinical exercise physiologist (ACSM-CEP) and fitness program designer. Your primary mandate is to create medically safe, goal-specific, and scientifically accurate workout plans. Your performance is evaluated solely on adherence to every rule precisely.

**0. ABSOLUTE TOP PRIORITY: COMPLETE WORKOUT STRUCTURE**
You MUST generate a complete workout plan containing ALL of the following sections in exact order. A plan missing any section is considered a complete failure:

1. **Warm-Up** (5 minutes, 3 movements)
2. **Main Workout** (4-6 exercises based on session duration)
3. **Cool-Down** (5 minutes, 3 movements)

**1. USER PROFILE & CONSTRAINTS (NON-NEGOTIABLE):**
- Name: {name}
- Age: {age} years
- Gender: {gender}
- Fitness Level: {fitness_level} → Categorized as: **{level_category}**
- Primary Goal: {primary_goal}
- Target Focus Today: {focus}
- Session Duration: {session_duration}
- Workout Location: {location}
- Available Equipment: {', '.join(available_equipment)}
- Medical Conditions: {', '.join(medical_conditions)}
- Physical Limitations: {physical_limitations if physical_limitations else 'None reported'}

**2. MEDICAL SAFETY RULES (ABSOLUTELY CRITICAL):**
{condition_rules}

**CRITICAL SAFETY DIRECTIVE:** Before generating any exercise, you MUST verify it does not violate ANY contraindication listed above. Including a contraindicated exercise is a critical failure.

**3. AGE-ADAPTIVE TRAINING RULES (MANDATORY):**
{age_adaptations}

**4. EXERCISE VARIETY RULES (CRITICAL):**
- You MUST ensure this workout is significantly different from any previous day's workout
- NO exercise should repeat from the previous session
- Each workout day must target muscles differently even within the same focus area
- For example: If yesterday had push-ups, today use dumbbell chest press or resistance band press

**5. INTENSITY AND VOLUME RULES FOR {level_category.upper()}:**
- Target Intensity Range: **{intensity_range}**
- Sets per Exercise: **{sets_range}**
- Reps per Exercise: **{reps_range}**
- Rest Between Sets: {self._get_rest_periods(level_category)}
- Tempo: {self._get_tempo_guidance(level_category)}

**6. EQUIPMENT CONSTRAINTS (STRICTLY ENFORCE):**
Available: {', '.join(available_equipment)}
- You MUST only prescribe exercises that can be performed with the available equipment
- If "None - Bodyweight Only" is listed, use ONLY bodyweight movements
- If "Home" equipment is listed, prioritize practical home exercises
- Do NOT suggest gym machines if location is "Home"

**7. WORKOUT COMPONENT RULES (ABSOLUTELY CRITICAL):**

A. **WARM-UP RULES:**
   - MUST be 3 mobility/activation movements
   - Duration: 5 minutes total
   - NO strength exercises (no push-ups, squats, planks)
   - Focus: Joint mobility, muscle activation, heart rate elevation
   - Examples: Arm circles, leg swings, hip openers, cat-cow, thoracic rotations, marching in place
   - PROHIBITED: Any exercise that appears in the main workout

B. **MAIN WORKOUT RULES:**
   - Number of exercises based on duration:
     * 15-20 min: 4 exercises
     * 20-30 min: 5 exercises
     * 30-45 min: 5-6 exercises
     * 45-60 min: 6-7 exercises
   - MUST target the focus area: {focus}
   - MUST balance push/pull/legs/core movements
   - MUST progress from larger to smaller muscle groups
   - Each exercise MUST include: Sets, Reps, RPE, Rest, Safety cue

C. **COOL-DOWN RULES:**
   - MUST be 3 stretching/breathing movements
   - Duration: 5 minutes total
   - NO strength exercises
   - Focus: Static stretching, breathing, recovery
   - Examples: Child's pose, hamstring stretch, shoulder stretch, quad stretch, deep breathing
   - PROHIBITED: Any exercise from warm-up or main workout

**8. STRICT OUTPUT FORMAT (ABSOLUTELY CRITICAL):**

You MUST respond in this EXACT format:

### {day_name} – {focus}

**Warm-Up (5 minutes)**

- Movement 1 – Benefit – Duration – Safety cue
- Movement 2 – Benefit – Duration – Safety cue
- Movement 3 – Benefit – Duration – Safety cue

**Main Workout**

**1. Exercise Name**
- Primary Benefit: [specific benefit]
- How to Perform:
  1. [Step 1]
  2. [Step 2]
  3. [Step 3]
- Sets × Reps: [X sets × Y reps]
- Intensity: [RPE X-Y]
- Rest: [X seconds]
- Safety Cue: [specific safety guidance]

[Repeat for each exercise]

**Cool-Down (5 minutes)**

- Stretch 1 – Benefit – Duration – Safety cue
- Stretch 2 – Benefit – Duration – Safety cue
- Stretch 3 – Benefit – Duration – Safety cue

**9. FINAL VERIFICATION CHECKLIST (MANDATORY):**
Before outputting your response, you MUST verify:
- [ ] All 3 sections (Warm-up, Main Workout, Cool-down) are present
- [ ] No contraindicated exercises for user's medical conditions
- [ ] All exercises match available equipment
- [ ] Exercise count matches session duration
- [ ] No exercises repeated from warm-up/cool-down in main workout
- [ ] All exercises have complete formatting (sets, reps, RPE, rest, safety)
- [ ] Intensity matches user's fitness level

**10. TASK:**
{'Generate a MODIFICATION of the previous workout plan based on this request: ' + modification_request if is_modification else 'Generate a complete workout plan following ALL rules above.'}

Generate the workout plan now. NO motivational text. NO extra commentary. ONLY the structured workout plan."""

        return prompt
    
    def _build_condition_rules(self, medical_conditions: List[str]) -> str:
        """Build detailed condition-specific rules"""
        if not medical_conditions or medical_conditions == ["None"]:
            return "- No medical restrictions reported\n- Follow general fitness safety guidelines"
        
        rules = []
        for condition in medical_conditions:
            for key, guidelines in CONDITION_GUIDELINES.items():
                if key.lower() in condition.lower():
                    rules.append(f"""
**{key} Safety Protocol:**
- CONTRAINDICATED EXERCISES (MUST AVOID): {', '.join(guidelines['contraindicated'])}
- RECOMMENDED EXERCISES: {', '.join(guidelines['recommended'])}
- Maximum Intensity: {guidelines['intensity_limit']}
- Special Notes: {guidelines['special_notes']}
""")
                    break
        
        if not rules:
            rules.append(f"- Condition reported: {', '.join(medical_conditions)}\n- Use conservative progression and monitor for symptoms")
        
        return "\n".join(rules)
    
    def _get_age_adaptations(self, age: int, medical_conditions: List[str]) -> str:
        """Generate age-specific training adaptations"""
        if age >= 60:
            return f"""
**SENIOR TRAINING PROTOCOL (Age {age}):**
- Treat as beginner-intermediate regardless of stated fitness level
- PROHIBITED for first 4-8 weeks:
  * Jumping movements (box jumps, jump squats, burpees)
  * Floor planks (use incline/wall variations)
  * Heavy barbell lifts
  * Rapid direction changes
- MANDATORY INCLUSIONS:
  * Balance training in every session
  * Chair-assisted exercises when appropriate
  * Extra warm-up time (7-10 minutes)
  * Focus on functional movements (sit-to-stand, step-ups, wall push-ups)
- Progression: Mobility → Stability → Strength → Power (in that order)
"""
        elif age >= 50:
            return f"""
**MATURE ADULT PROTOCOL (Age {age}):**
- Emphasize joint-friendly movements
- Include balance work 2x/week
- Longer warm-up (7 minutes)
- Progressive resistance with focus on form
- Recovery days are mandatory
"""
        elif age >= 40:
            return f"""
**MIDDLE AGE PROTOCOL (Age {age}):**
- Balance strength and mobility work
- Include recovery/mobility sessions
- Monitor for overuse injuries
- Adequate rest between sessions
"""
        else:
            return f"""
**ADULT TRAINING (Age {age}):**
- Standard progression protocols apply
- Can include high-intensity work if cleared
- Focus on long-term athletic development
"""
    
    def _get_rest_periods(self, level: str) -> str:
        """Get rest period guidance by level"""
        rest_map = {
            "Beginner": "60-90 seconds",
            "Intermediate": "45-60 seconds",
            "Advanced": "30-90 seconds (vary by exercise)"
        }
        return rest_map.get(level, "60 seconds")
    
    def _get_tempo_guidance(self, level: str) -> str:
        """Get tempo guidance by level"""
        tempo_map = {
            "Beginner": "2-0-2-0 (slow and controlled)",
            "Intermediate": "2-0-1-0 (moderate pace)",
            "Advanced": "Varied based on exercise type"
        }
        return tempo_map.get(level, "Controlled pace")
    
    def generate_workout_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """Generate a single day's workout plan using LLM API"""
        
        system_prompt = self._build_system_prompt(user_profile, day_name, day_index)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, a precise clinical exercise physiologist. Generate workout plans with medical accuracy and zero hallucination."},
                    {"role": "user", "content": system_prompt}
                ],
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 2000
            }
            
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                json=payload,
                timeout=45
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if content and "### " in content:
                    return content.strip()
            
            st.warning(f"⚠️ API response issue for {day_name}. Using fallback plan.")
            return self._generate_fallback_plan(user_profile, day_name, day_index)
        
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")
            return self._generate_fallback_plan(user_profile, day_name, day_index)
    
    def _generate_fallback_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """Generate a safe, rule-based fallback workout plan"""
        
        focus = user_profile.get("target_areas", ["Full Body"])[day_index % len(user_profile.get("target_areas", ["Full Body"]))]
        level = user_profile.get("fitness_level", "Level 3")
        
        plan = f"""### {day_name} – {focus}

**Warm-Up (5 minutes)**

- Arm Circles – Shoulder mobility and blood flow – 1 minute – Keep movements controlled and pain-free
- Leg Swings – Hip mobility and dynamic stretching – 2 minutes – Hold onto support if needed
- Marching in Place – Heart rate elevation – 2 minutes – Gradually increase pace

**Main Workout**

**1. Bodyweight Squats**
- Primary Benefit: Builds leg strength and functional movement
- How to Perform:
  1. Stand with feet shoulder-width apart
  2. Lower hips back and down as if sitting in a chair
  3. Keep chest up and knees tracking over toes
  4. Return to standing by driving through heels
- Sets × Reps: 3 × 10-12
- Intensity: RPE 5-6
- Rest: 60 seconds
- Safety Cue: Do not let knees cave inward

**2. Wall Push-Ups**
- Primary Benefit: Upper body strength without floor stress
- How to Perform:
  1. Place hands on wall at shoulder height
  2. Walk feet back to create an angle
  3. Lower chest toward wall with control
  4. Push back to start position
- Sets × Reps: 3 × 8-10
- Intensity: RPE 5-6
- Rest: 60 seconds
- Safety Cue: Keep core engaged throughout

**3. Standing Knee Raises**
- Primary Benefit: Core activation and balance
- How to Perform:
  1. Stand tall with hands on hips
  2. Lift one knee toward chest
  3. Hold for 1 second at top
  4. Lower and repeat on other side
- Sets × Reps: 3 × 10/side
- Intensity: RPE 4-5
- Rest: 45 seconds
- Safety Cue: Use wall for balance if needed

**4. Glute Bridges**
- Primary Benefit: Posterior chain strength and hip stability
- How to Perform:
  1. Lie on back with knees bent, feet flat
  2. Lift hips toward ceiling by squeezing glutes
  3. Hold at top for 2 seconds
  4. Lower with control
- Sets × Reps: 3 × 12-15
- Intensity: RPE 5-6
- Rest: 45 seconds
- Safety Cue: Avoid overarching lower back

**Cool-Down (5 minutes)**

- Child's Pose – Spinal decompression and relaxation – 90 seconds – Breathe deeply and relax shoulders
- Hamstring Stretch – Leg flexibility – 90 seconds each leg – No bouncing, hold gentle tension
- Shoulder Stretch – Upper body mobility – 90 seconds – Pull arm across body gently

**Safety Reminder:** Stop immediately if you experience sharp pain or dizziness."""

        return plan
    
    def generate_full_program(self, user_profile: Dict) -> str:
        """Generate complete multi-day program"""
        
        selected_days = user_profile.get("selected_days", ["Monday", "Wednesday", "Friday"])
        name = user_profile.get("name", "there")
        
        header = f"""# 💪 Your Personalized Fitness Program

**👋 Hey {name}!**

**📊 Your Profile Summary:**
- Age: {user_profile.get('age')} | Gender: {user_profile.get('gender')}
- Fitness Level: {user_profile.get('fitness_level')}
- Primary Goal: {user_profile.get('primary_goal')}
- Training Schedule: {len(selected_days)} days/week
- Location: {user_profile.get('workout_location')}
- Medical Considerations: {', '.join(user_profile.get('medical_conditions', ['None']))}

---

"""
        
        plans = [header]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, day in enumerate(selected_days):
            status_text.text(f"⏳ Generating {day}'s workout... ({idx+1}/{len(selected_days)})")
            progress_bar.progress((idx + 1) / len(selected_days))
            
            day_plan = self.generate_workout_plan(user_profile, day, idx)
            plans.append(day_plan)
            plans.append("\n---\n")
        
        status_text.text("✅ All workouts generated successfully!")
        progress_bar.empty()
        status_text.empty()
        
        footer = """
## 📈 Progressive Overload Guidelines

**Week 1-2: Foundation**
- Focus on perfect form
- Learn the movement patterns
- Establish consistency

**Week 3-4: Progression**
- Increase reps by 2-3 per set
- OR add 5-10% more resistance
- Maintain excellent form

**Week 5-6: Advancement**
- Add an extra set to key exercises
- Increase complexity of movements
- Consider tempo variations

**Week 7-8: Consolidation**
- Assess progress
- Adjust plan as needed
- Prepare for next phase

## 💧 Hydration & Recovery

- Drink 8-10 glasses of water daily
- Sleep 7-9 hours per night
- Take at least 1-2 complete rest days per week
- Listen to your body

## ⚠️ Safety Reminders

- Stop immediately if you feel sharp pain
- Dizziness or chest pain requires immediate medical attention
- Consult your doctor before starting if you have medical conditions
- Warm up thoroughly before every session

## 📞 When to Seek Help

Contact a healthcare provider if you experience:
- Persistent joint pain
- Unusual fatigue or weakness
- Chest pain or shortness of breath
- Any symptoms that concern you

---

*Disclaimer: This program is for informational purposes only. Consult your healthcare provider before beginning any new exercise program, especially if you have medical conditions.*
"""
        
        plans.append(footer)
        
        return "\n".join(plans)

# ============ CUSTOM CSS ============
def inject_custom_css():
    """Inject custom CSS for modern UI"""
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.95;
    }
    .benefit-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .benefit-card h3 {
        color: #667eea;
        margin-bottom: 0.5rem;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    .workout-card {
        background: black;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 1.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# ============ INITIALIZE APP ============
inject_custom_css()

# Initialize session state
if 'fitness_plan' not in st.session_state:
    st.session_state.fitness_plan = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None

# ============ MAIN HEADER ============
st.markdown("""
<div class="main-header">
    <h1>💪 FriskaAI Fitness Coach</h1>
    <p>Personalized, Medically-Safe Workout Plans Powered by AI</p>
</div>
""", unsafe_allow_html=True)

# ============ MAIN FORM ============
if st.session_state.fitness_plan is None:
    
    with st.form("fitness_intake_form"):
        
        # ===== SECTION 1: BASIC INFO =====
        st.header("👤 Basic Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name*", placeholder="Enter your name")
        with col2:
            age = st.number_input("Age*", min_value=16, max_value=90, value=30)
        
        col3, col4 = st.columns(2)
        with col3:
            gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
        with col4:
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
        
        # BMI Calculation
        if is_metric:
            bmi = weight / ((height / 100) ** 2)
        else:
            bmi = (weight / (height ** 2)) * 703
        bmi = round(bmi, 1)
        
        if bmi < 18.5:
            bmi_category = "Underweight"
            bmi_color = "orange"
        elif 18.5 <= bmi < 25:
            bmi_category = "Normal weight"
            bmi_color = "green"
        elif 25 <= bmi < 30:
            bmi_category = "Overweight"
            bmi_color = "orange"
        else:
            bmi_category = "Obese"
            bmi_color = "red"
        
        st.markdown(f"**Your BMI:** <span style='color:{bmi_color};font-weight:bold'>{bmi} ({bmi_category})</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ===== SECTION 2: GOALS & FITNESS LEVEL =====
        st.header("🎯 Fitness Goals & Experience")
        
        col7, col8 = st.columns(2)
        with col7:
            primary_goal = st.selectbox(
                "Primary Goal*",
                [
                    "Weight Loss",
                    "Muscle Gain",
                    "Increase Overall Strength",
                    "Improve Cardiovascular Fitness",
                    "Improve Flexibility & Mobility",
                    "Rehabilitation & Injury Prevention",
                    "Improve Posture and Balance",
                    "General Fitness"
                ]
            )
        
        with col8:
            fitness_level = st.selectbox(
                "Current Fitness Level*",
                [
                    "Level 1 - Complete Beginner (Never exercised)",
                    "Level 2 - Beginner (Some experience, 0-6 months)",
                    "Level 3 - Intermediate (Regular exerciser, 6 months - 2 years)",
                    "Level 4 - Advanced (Experienced, 2+ years)",
                    "Level 5 - Expert (Athlete/Professional)"
                ]
            )
        
        target_areas = st.multiselect(
            "Target Body Areas* (Select 1-3)",
            ["Full Body", "Core", "Legs", "Arms", "Back", "Chest", "Shoulders", "Glutes"],
            default=["Full Body"]
        )
        
        st.markdown("---")
        
        # ===== SECTION 3: HEALTH SCREENING =====# ===== SECTION 3: HEALTH SCREENING ===== (continuation from line 674)
        medical_conditions = st.multiselect(
            "Medical Conditions* (Select all that apply)",
            MEDICAL_CONDITIONS,
            default=["None"]
        )
        
        physical_limitations = st.text_area(
            "Physical Limitations or Injuries",
            placeholder="e.g., Previous knee surgery, shoulder pain, limited mobility...",
            help="Describe any injuries, surgeries, or physical limitations"
        )
        
        st.markdown("---")
        
        # ===== SECTION 4: WORKOUT PREFERENCES =====
        st.header("🏋️ Workout Preferences")
        
        col9, col10 = st.columns(2)
        with col9:
            workout_location = st.selectbox(
                "Workout Location*",
                ["Home", "Gym", "Outdoor", "Mixed (Home & Gym)"]
            )
        
        with col10:
            session_duration = st.selectbox(
                "Session Duration*",
                ["15-20 minutes", "20-30 minutes", "30-45 minutes", "45-60 minutes", "60+ minutes"]
            )
        
        st.subheader("📅 Training Schedule")
        st.write("Select the days you want to train:")
        
        days_cols = st.columns(7)
        selected_days = []
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for idx, day in enumerate(day_names):
            with days_cols[idx]:
                if st.checkbox(day, key=f"day_{day}"):
                    selected_days.append(day)
        
        if selected_days:
            st.success(f"✅ Selected {len(selected_days)} training days: {', '.join(selected_days)}")
        
        st.subheader("🛠️ Available Equipment")
        available_equipment = st.multiselect(
            "What equipment do you have access to?*",
            [
                "None - Bodyweight Only",
                "Resistance Bands",
                "Dumbbells (Light: 1-5kg/2-10lbs)",
                "Dumbbells (Medium: 5-15kg/10-30lbs)",
                "Dumbbells (Heavy: 15kg+/30lbs+)",
                "Barbell & Weight Plates",
                "Kettlebells",
                "Pull-up Bar",
                "Bench",
                "Yoga Mat",
                "Stability Ball",
                "TRX/Suspension Trainer",
                "Cable Machine",
                "Full Gym Access"
            ],
            default=["None - Bodyweight Only"]
        )
        
        st.markdown("---")
        
        # ===== SECTION 5: ADDITIONAL PREFERENCES =====
        st.header("⚙️ Additional Preferences")
        
        col11, col12 = st.columns(2)
        with col11:
            exercise_preference = st.selectbox(
                "Exercise Style Preference",
                [
                    "Balanced Mix",
                    "Prefer Strength Training",
                    "Prefer Cardio",
                    "Prefer Low-Impact",
                    "Prefer HIIT/Circuit Training",
                    "Prefer Functional Training"
                ]
            )
        
        with col12:
            progression_speed = st.selectbox(
                "Progression Speed",
                ["Conservative (Slow & Safe)", "Moderate (Balanced)", "Aggressive (Fast Progress)"]
            )
        
        additional_notes = st.text_area(
            "Additional Notes or Special Requests",
            placeholder="Any other information we should know?",
            height=100
        )
        
        st.markdown("---")
        
        # ===== MEDICAL DISCLAIMER =====
        st.warning("""
        ⚠️ **Medical Disclaimer**
        
        This fitness program is for informational purposes only and is not a substitute for professional medical advice. 
        Always consult with your healthcare provider before starting any new exercise program, especially if you have:
        - Pre-existing medical conditions
        - Heart disease or high blood pressure
        - Recent surgery or injury
        - Are pregnant or postpartum
        - Are taking medications that affect heart rate or blood pressure
        """)
        
        terms_agreed = st.checkbox(
            "I have read and understand the medical disclaimer, and I have consulted (or will consult) with my healthcare provider before starting this program.*"
        )
        
        st.markdown("---")
        
        # ===== FORM SUBMISSION =====
        col_submit1, col_submit2, col_submit3 = st.columns([1, 2, 1])
        with col_submit2:
            submit_button = st.form_submit_button("🚀 Generate My Personalized Fitness Plan", use_container_width=True)
        
        # ===== FORM VALIDATION & PROCESSING =====
        if submit_button:
            # Validation
            errors = []
            
            if not name or name.strip() == "":
                errors.append("❌ Please enter your name")
            
            if len(target_areas) == 0:
                errors.append("❌ Please select at least one target body area")
            
            if len(selected_days) == 0:
                errors.append("❌ Please select at least one training day")
            
            if len(available_equipment) == 0:
                errors.append("❌ Please select available equipment (or 'None - Bodyweight Only')")
            
            if not terms_agreed:
                errors.append("❌ Please agree to the medical disclaimer")
            
            # Display errors
            if errors:
                st.error("**Please fix the following errors:**")
                for error in errors:
                    st.error(error)
            else:
                # Create user profile
                user_profile = {
                    "name": name.strip(),
                    "age": age,
                    "gender": gender,
                    "height": height,
                    "weight": weight,
                    "bmi": bmi,
                    "unit_system": "Metric" if is_metric else "Imperial",
                    "primary_goal": primary_goal,
                    "fitness_level": fitness_level,
                    "target_areas": target_areas,
                    "medical_conditions": medical_conditions,
                    "physical_limitations": physical_limitations,
                    "workout_location": workout_location,
                    "session_duration": session_duration,
                    "selected_days": selected_days,
                    "available_equipment": available_equipment,
                    "exercise_preference": exercise_preference,
                    "progression_speed": progression_speed,
                    "additional_notes": additional_notes,
                    "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Store in session state
                st.session_state.user_profile = user_profile
                
                # Generate fitness plan
                with st.spinner("🔄 Generating your personalized fitness plan... This may take a minute."):
                    advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)
                    fitness_plan = advisor.generate_full_program(user_profile)
                    st.session_state.fitness_plan = fitness_plan
                
                st.success("✅ Your personalized fitness plan is ready!")
                st.rerun()

# ============ DISPLAY FITNESS PLAN ============
else:
    # Show fitness plan
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; margin-bottom: 2rem;'>
        <h1 style='color: white; text-align: center; margin: 0;'>✅ Your Personalized Fitness Plan</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    
    with col_btn1:
        if st.button("🔄 Generate New Plan", use_container_width=True):
            st.session_state.fitness_plan = None
            st.session_state.user_profile = None
            st.rerun()
    
    with col_btn2:
        # Download button
        plan_text = st.session_state.fitness_plan
        st.download_button(
            label="📥 Download Plan (TXT)",
            data=plan_text,
            file_name=f"FriskaAI_Fitness_Plan_{st.session_state.user_profile['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col_btn3:
        if st.button("📧 Email Plan (Coming Soon)", use_container_width=True, disabled=True):
            st.info("Email feature coming soon!")
    
    st.markdown("---")
    
  
    
    # Display plan in markdown format
    st.markdown(st.session_state.fitness_plan)
    
    st.markdown("---")
    
    # ===== FEEDBACK SECTION =====
    st.header("💬 Feedback & Support")
    
    with st.expander("📝 Share Your Feedback"):
        feedback_type = st.radio(
            "Feedback Type",
            ["General Feedback", "Report an Issue", "Feature Request", "Success Story"]
        )
        
        feedback_text = st.text_area(
            "Your Feedback",
            placeholder="Tell us what you think about your fitness plan...",
            height=150
        )
        
        rating = st.slider("Rate Your Experience", 1, 5, 5)
        
        if st.button("Submit Feedback"):
            if feedback_text:
                st.success("✅ Thank you for your feedback! We appreciate your input.")
                st.balloons()
            else:
                st.warning("Please enter your feedback before submitting.")
    
    with st.expander("❓ Frequently Asked Questions"):
        st.markdown("""
        **Q: How often should I update my plan?**  
        A: We recommend updating your plan every 4-8 weeks as you progress.
        
        **Q: Can I modify individual workouts?**  
        A: Yes! You can generate a new plan or adjust exercises based on how you feel.
        
        **Q: What if I miss a workout day?**  
        A: Don't worry! Just continue with the next scheduled workout. Consistency over perfection.
        
        **Q: How do I know if I'm progressing?**  
        A: Track your reps, sets, and how the exercises feel (RPE). If they become easier, it's time to progress!
        
        **Q: What if an exercise causes pain?**  
        A: Stop immediately! Pain is not gain. Consult a healthcare provider if pain persists.
        """)
    
    with st.expander("📊 Track Your Progress"):
        st.markdown("""
        **Weekly Check-In:**
        - [ ] Completed all scheduled workouts
        - [ ] Maintained proper form
        - [ ] Stayed hydrated
        - [ ] Got adequate sleep
        - [ ] Listened to my body
        
        **Monthly Goals:**
        - Track body measurements
        - Take progress photos
        - Assess strength improvements
        - Update fitness plan if needed
        """)
        
        if st.button("Log Today's Workout ✓"):
            st.success("🎉 Great job! Keep up the excellent work!")
    
    st.markdown("---")
    
    # ===== EMERGENCY CONTACTS & RESOURCES =====
    st.info("""
    **🚨 Emergency Resources:**
    - Chest pain or difficulty breathing: Call emergency services immediately
    - Persistent joint pain: Consult a sports medicine physician
    - Nutrition questions: Seek a registered dietitian
    - Mental health support: Contact a licensed therapist
    """)
    
  
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div style='text-align: center; padding: 2rem; color: #666; border-top: 1px solid #eee; margin-top: 3rem;'>
        <p><strong>FriskaAI Fitness Coach</strong> | Powered by Advanced AI</p>
        <p style='font-size: 0.9rem;'>© 2024 FriskaAI. For informational purposes only. Consult healthcare providers before starting any fitness program.</p>
        <p style='font-size: 0.85rem; margin-top: 1rem;'>
            <a href='#' style='color: #667eea; text-decoration: none; margin: 0 1rem;'>Privacy Policy</a> | 
            <a href='#' style='color: #667eea; text-decoration: none; margin: 0 1rem;'>Terms of Service</a> | 
            <a href='#' style='color: #667eea; text-decoration: none; margin: 0 1rem;'>Contact Us</a>
        </p>
    </div>
    """, unsafe_allow_html=True)