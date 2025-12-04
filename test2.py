import streamlit as st
import requests
from typing import Dict, List, Optional, Set
import re
from datetime import datetime
import pandas as pd

# ============ CONFIGURATION ============
# NOTE: The API key and Endpoint URL are set for an Azure Mistral deployment.
# CRITICAL FIX: The API key header is corrected below to use 'Authorization: Bearer'
# to address the Status 400 error: "Auth token must be passed as a header called Authorization"
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"

st.set_page_config(
    page_title="FriskaAI Fitness Coach",
    page_icon="💪",
    layout="wide"
)

# ============ LOAD EXCEL CONDITION DATABASE ============
@st.cache_data
def load_condition_database():
    """Load condition database from Excel file"""
    try:
        # Try to load the Excel file
        # CRITICAL: Ensure the Excel file name is correct and accessible
        df = pd.read_excel("Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx")
        
        # Convert to dictionary for easier access
        condition_db = {}
        # Ensure 'Condition' column exists
        if 'Condition' not in df.columns:
            # Replaced st.error with print/logging for non-display function
            return {}
            
        for _, row in df.iterrows():
            condition_name = row['Condition']
            # Convert NaN to empty string for safe string formatting later
            condition_db[condition_name] = {
                'medications': row.get('Medication(s)', pd.NA),
                'direct_impact': row.get('Direct Exercise Impact', pd.NA),
                'indirect_impact': row.get('Indirect Exercise Impacts', pd.NA),
                'contraindicated': row.get('Contraindicated Exercises', pd.NA),
                'modified_safer': row.get('Modified / Safer Exercises', pd.NA)
            }
            # Replace pd.NA with empty string for clean output in prompt
            for key in condition_db[condition_name]:
                if pd.isna(condition_db[condition_name][key]):
                    condition_db[condition_name][key] = ""
                    
        # st.success("Condition database loaded successfully.") # Removed for non-display function
        return condition_db
    except FileNotFoundError:
        # st.warning(f"Could not find Excel file 'Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx'. Using fallback database.") # Removed for non-display function
        return {}
    except Exception as e:
        # st.warning(f"Could not load condition database: {str(e)}. Using fallback database.") # Removed for non-display function
        return {}

# Load condition database
CONDITION_DATABASE = load_condition_database()

# ============ UPDATED MEDICAL CONDITIONS LIST ============
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

# ============ UPDATED FITNESS LEVELS WITH RPE ============
FITNESS_LEVELS = {
    "Level 1 – Assisted / Low Function": {
        "description": "Needs support for balance, limited endurance, sedentary >6 months",
        "exercises": "Chair exercises, wall push-ups, step taps, light bands",
        "rpe_range": "3-4",
        "characteristics": [
            "Requires support for balance",
            "Limited endurance (<10 min continuous activity)",
            "Sedentary for >6 months",
            "May need assistance with daily activities"
        ]
    },
    "Level 2 – Beginner Functional": {
        "description": "Can perform light bodyweight tasks, mild conditions under control",
        "exercises": "Slow tempo bodyweight + mobility drills",
        "rpe_range": "4-5",
        "characteristics": [
            "Can perform light bodyweight movements",
            "Mild medical conditions under control",
            "Some exercise experience but inconsistent",
            "Can sustain 10-15 min activity"
        ]
    },
    "Level 3 – Moderate / Independent": {
        "description": "Can perform unassisted movements with mild fatigue",
        "exercises": "Resistance bands, light weights, low-impact cardio",
        "rpe_range": "5-7",
        "characteristics": [
            "Independent with most movements",
            "Can handle moderate intensity",
            "Regular activity 2-3x/week",
            "Can sustain 20-30 min sessions"
        ]
    },
    "Level 4 – Active Wellness": {
        "description": "No severe limitations, accustomed to regular activity",
        "exercises": "Moderate intensity strength + balance training",
        "rpe_range": "6-8",
        "characteristics": [
            "Regular exercise 3-4x/week",
            "Good movement quality",
            "Can handle varied intensities",
            "Can sustain 30-45 min sessions"
        ]
    },
    "Level 5 – Adaptive Advanced": {
        "description": "Experienced user managing mild conditions",
        "exercises": "Structured strength split, low-impact cardio, yoga",
        "rpe_range": "7-9",
        "characteristics": [
            "Consistent training 4-6x/week",
            "Advanced movement patterns",
            "Self-manages conditions effectively",
            "Can sustain 45-60+ min sessions"
        ]
    }
}

class FitnessAdvisor:
    """Enhanced fitness planning engine with proper API integration"""
    
    def __init__(self, api_key: str, endpoint_url: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        
        # UPDATED: Goal programming WITHOUT RPE (moved to levels)
        self.goal_programming_guidelines = {
            "Weight Loss": {
                "priority": "Low to moderate-intensity cardio + resistance for large muscle groups",
                "rep_range": "12-20",
                "rest": "30-45 seconds",
                "cardio_focus": "60-70% of workout time",
                "sets": "2-3" # Added sets
            },
            "Muscle Gain": {
                "priority": "Progressive overload resistance training, controlled tempo",
                "rep_range": "6-12",
                "rest": "60-90 seconds",
                "volume": "3-5 sets per exercise",
                "sets": "3-5" # Added sets
            },
            "Increase Overall Strength": {
                "priority": "Compound lifts, progressive loading, mobility work",
                "rep_range": "4-8",
                "rest": "90-180 seconds",
                "focus": "Heavy compound movements",
                "sets": "3-5" # Added sets
            },
            "Improve Cardiovascular Fitness": {
                "priority": "Aerobic/interval protocols, recovery days",
                "intensity": "60-80% max HR",
                "modality": "Continuous or interval training",
                "sets": "N/A"
            },
            "Improve Flexibility & Mobility": {
                "priority": "Stretching, joint mobility, dynamic ROM",
                "hold_duration": "30-60 seconds per stretch",
                "focus": "Full range of motion",
                "sets": "N/A"
            },
            "Rehabilitation & Injury Prevention": {
                "priority": "Corrective exercises, stability, low-load resistance",
                "rep_range": "10-15",
                "rest": "60-90 seconds",
                "exclude": "High-impact, ballistic movements",
                "sets": "2-3" # Added sets
            },
            "Improve Posture and Balance": {
                "priority": "Core activation, mobility, balance",
                "focus": "Postural muscles, single-leg work",
                "sets": "2-3" # Added sets
            },
            "General Fitness": {
                "priority": "Balanced approach: cardio, strength, flexibility",
                "rep_range": "10-15",
                "rest": "45-60 seconds",
                "sets": "2-3" # Added sets
            }
        }
    
    def _get_condition_details_from_db(self, condition: str) -> Dict:
        """Get condition details from loaded Excel database"""
        if condition in CONDITION_DATABASE:
            # Safely return the data, defaulting to 'N/A' or conservative values if empty string
            return {k: v if v else 'N/A' for k, v in CONDITION_DATABASE[condition].items()}
        
        # Fallback to hardcoded if not in Excel (only for major conditions)
        fallback_db = {
            "Hypertension (High Blood Pressure)": {
                "medications": "ACE inhibitors, Beta-blockers, Diuretics",
                "direct_impact": "May reduce exercise capacity, affect heart rate response",
                "indirect_impact": "Dizziness, fatigue",
                "contraindicated": "Valsalva maneuvers, heavy isometric holds, overhead pressing without control",
                "modified_safer": "Controlled breathing, moderate resistance, continuous breathing pattern"
            },
            "Type 2 Diabetes": {
                "medications": "Metformin, Insulin, Sulfonylureas",
                "direct_impact": "Risk of hypoglycemia during exercise",
                "indirect_impact": "Fatigue, neuropathy, vision issues",
                "contraindicated": "High-intensity intervals without medical clearance, prolonged fasting exercise",
                "modified_safer": "Moderate-intensity steady state, check blood glucose pre/post workout"
            }
        }
        
        return fallback_db.get(condition, {
            "medications": "Unknown",
            "direct_impact": "Use conservative approach",
            "indirect_impact": "Monitor for symptoms",
            "contraindicated": "High-risk movements (e.g., heavy lifting, ballistic) due to unknown risk",
            "modified_safer": "Low-impact, controlled movements"
        })
    
    def _build_system_prompt(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        previous_plans: Dict, 
        workout_category: str = "Full Body"
    ) -> str:
        """Build comprehensive system prompt with all fixes and goal alignment updates"""
        
        # Extract profile
        name = user_profile.get("name", "User")
        age = user_profile.get("age", 30)
        gender = user_profile.get("gender", "Other")
        bmi = user_profile.get("bmi", 22)
        fitness_level = user_profile.get("fitness_level", "Level 3 – Moderate / Independent")
        primary_goal = user_profile.get("primary_goal", "General Fitness")
        secondary_goal = user_profile.get("secondary_goal", "None")
        medical_conditions = user_profile.get("medical_conditions", ["None"])
        physical_limitations = user_profile.get("physical_limitations", "")
        session_duration = user_profile.get("session_duration", "30-45 minutes") # Get duration for prompt context
        
        # Get level-specific RPE and exercises
        level_data = FITNESS_LEVELS.get(fitness_level, FITNESS_LEVELS["Level 3 – Moderate / Independent"])
        level_rpe = level_data['rpe_range']
        
        # Get goal guidelines
        goal_guidelines = self.goal_programming_guidelines.get(primary_goal, {})
        
        # *** GOAL/LEVEL ALIGNMENT OVERRIDE ***
        target_rpe = level_rpe
        target_sets = goal_guidelines.get('sets', '2-3')
        target_reps = goal_guidelines.get('rep_range', '10-15')
        target_rest = goal_guidelines.get('rest', '45-60 seconds')
        
        rpe_override_note = ""
        if primary_goal == "Muscle Gain" and fitness_level in ["Level 1 – Assisted / Low Function", "Level 2 – Beginner Functional"]:
            target_rpe = "5-7" # Override for stimulus
            target_sets = "3"   # Enforce 3 sets minimum for hypertrophy stimulus
            target_reps = "6-12"
            rpe_override_note = (
                "**⚠️ RPE OVERRIDE FOR MUSCLE GAIN: Despite the Level 1 constraints, you MUST target RPE 5-7 "
                "to create sufficient mechanical tension for muscle hypertrophy. The exercises themselves "
                "must remain Level 1 (seated, assisted, stable), but the weight/band used MUST be challenging "
                "enough to achieve RPE 5-7 by the last few reps. DO NOT use RPE 3-4. Target 3 Sets.**"
            )
        # **************************************************
        
        # Determine the Focus for the workout (e.g., Lower Focus, Upper Focus, Core Focus)
        focus_map = {0: "Lower Focus", 1: "Upper Focus", 2: "Core Focus"}
        day_focus = focus_map.get(day_index % 3, "Balanced Focus")
        
        # *** DURATION FIX: Reduce exercise count for short sessions ***
        # If duration is 15-20 min, restrict main exercises to 4-5 total.
        max_main_exercises = "4-5" if session_duration in ["15-20 minutes", "20-30 minutes"] else "6-8"
        
        prompt = f"""You are FriskaAI, an expert clinical exercise physiologist (ACSM-CEP).
Your primary role is to ensure **MAXIMUM SAFETY** (especially for Level 1/Medical Conditions/Limitations) while **OPTIMIZING FOR THE PRIMARY GOAL**.

**USER PROFILE:**
- Name: {name}
- Age: {age} | Gender: {gender} | BMI: {bmi}
- Fitness Level: {fitness_level}
  * RPE Range (Baseline): {level_rpe} (Rate of Perceived Exertion)
  * Description: {level_data['description']}
  * Appropriate Exercises: {level_data['exercises']}
- **Session Duration:** {session_duration} (Target time is critical!)

**GOALS:**
- Primary Goal: {primary_goal}
  * {goal_guidelines.get('priority', 'Balanced fitness approach')}
  * Rep Range: {target_reps}
  * Rest: {target_rest}
  * Sets: {target_sets}
"""

        if secondary_goal and secondary_goal != "None":
            secondary_guidelines = self.goal_programming_guidelines.get(secondary_goal, {})
            prompt += f"""
- Secondary Goal: {secondary_goal}
  * {secondary_guidelines.get('priority', 'Support primary goal')}
"""

        # Add all previous plans for variety check
        if previous_plans:
            prompt += "\n**PREVIOUS WORKOUTS THIS WEEK (CRITICAL FOR VARIETY):**\n"
            for day, plan_data in previous_plans.items():
                if plan_data['success']:
                    # Simple text summary is enough for the AI to understand what was used
                    prompt += f"- **{day}**: Previously generated plan content (focus on exercise names/types): \n```\n{plan_data['plan'][:300]}...\n```\n"

        # CRITICAL: Physical limitations section
        if physical_limitations and physical_limitations.strip():
            prompt += f"""

**PHYSICAL LIMITATIONS (CRITICAL - MUST ACCOMMODATE):**
{physical_limitations}

**ACTION REQUIRED (LIMITATIONS):**
1. Analyze each limitation carefully
2. Exclude ANY exercise that could aggravate these limitations
3. Provide alternative exercises that work around limitations
4. Include specific safety cues related to these limitations
"""

        # Medical conditions with Excel database
        if medical_conditions and medical_conditions != ["None"]:
            prompt += f"""

**MEDICAL CONDITIONS (ZERO TOLERANCE - STRICT SAFETY):**
"""
            for condition in medical_conditions:
                if condition != "None":
                    cond_data = self._get_condition_details_from_db(condition)
                    prompt += f"""
**{condition}:**
- Medications: {cond_data.get('medications', 'N/A')}
- Direct Exercise Impact: {cond_data.get('direct_impact', 'Unknown')}
- Indirect Impacts: {cond_data.get('indirect_impact', 'Unknown')}
- ❌ CONTRAINDICATED: {cond_data.get('contraindicated', 'High-risk movements')}
- ✓ MODIFIED/SAFER: {cond_data.get('modified_safer', 'Low-impact alternatives')}
"""

        prompt += f"""

**TODAY'S WORKOUT:**
Day: {day_name} (Day {day_index + 1})
Category: {workout_category} ({day_focus})

**MANDATORY STRUCTURE (Strictly follow this formatting, including dashes and parentheses/brackets. USE DOUBLE NEWLINES (MARKDOWN PARAGRAPHS) TO SEPARATE ALL SECTIONS AND PARAMETERS FOR READABILITY):**

{day_name} – {workout_category} ({day_focus}) Focus

Warm-Up (5-7 minutes)
[Movement] – [Purpose] – [Duration/Reps] – [Safety Note]

[Movement] – [Purpose] – [Duration/Reps] – [Safety Note]

[Movement] – [Purpose] – [Duration/Reps] – [Safety Note]

[Movement] – [Purpose] – [Duration/Reps] – [Safety Note]

Main Workout (Target: {workout_category} ({day_focus}))
**CRITICAL: Include exactly {max_main_exercises} main exercises to fit the {session_duration} target time.**

[Exercise Name]
Benefit: [Benefit statement for {primary_goal}]

How to Perform:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Sets: **{target_sets}**

Reps: **{target_reps}**

Intensity: **RPE {target_rpe}**

Rest: **{target_rest}**

Equipment: [From available list]

Safety Cue: [Specific to limitations/conditions]

[Repeat for a total of {max_main_exercises} exercises]

Cool-Down (5-7 minutes)
[Stretch] – [Target] – [60-90 seconds] – [Safety Note]

[Stretch] – [Target] – [60-90 seconds] – [Safety Note]

[Stretch] – [Target] – [60-90 seconds] – [Safety Note]

[Stretch] – [Target] – [60-90 seconds] – [Safety Note]

**CRITICAL RULES:**
1. ALL exercises must match {fitness_level} complexity (e.g., seated, assisted, wall-supported).
2. ZERO contraindicated exercises for: {', '.join(medical_conditions)}
3. MUST accommodate physical limitations: {physical_limitations if physical_limitations else 'None'}
4. RPE must be **{target_rpe}** (Use the prescribed RPE).
5. **CRITICAL: Ensure STIMULUS VARIETY**. Do not repeat the exact same **Main Workout** exercise across multiple days (if previous plans exist). Use variations.
6. Support {primary_goal} with every exercise choice.

{rpe_override_note}

Generate the complete workout plan now in English only.
"""
        
        return prompt
    
    def generate_workout_plan(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        previous_plans: Dict, 
        workout_category: str = "Full Body"
    ) -> Dict:
        """Generate workout plan with fixed API call"""
        
        try:
            # The prompt is now generated outside this method in the main loop
            # and passed to the API call directly via the 'user' content.
            # We assume the caller (main function) provides the complete system prompt
            # in the session state for display. Here we re-fetch it or generate it
            # if we were to strictly follow the original logic, but for the
            # purpose of displaying, we will rely on the main function calling
            # _build_system_prompt separately.
            
            # Since the structure passes all required params, let's just generate the prompt here again
            # for the API call payload.
            system_prompt = self._build_system_prompt(
                user_profile, day_name, day_index, previous_plans, workout_category
            )
            
            # FIXED: Proper API call - Using 'Authorization: Bearer' to fix 400 error
            headers = {
                "Content-Type": "application/json",
                # CRITICAL FIX for 400 error: Use Bearer token authorization
                "Authorization": f"Bearer {self.api_key}" 
            }
            
            payload = {
                "model": "mistral-small",
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, an expert clinical exercise physiologist. Prioritize safety and follow all instructions strictly."},
                    {"role": "user", "content": system_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            
            response = requests.post(self.endpoint_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                # Log the full response text for debugging
                st.error(f"API Error {response.status_code}: {response.text}")
                # Use fallback plan, but capture the error message
                return {
                    "success": False,
                    "plan": self._generate_fallback_plan(user_profile, day_name, workout_category),
                    "error": f"API returned {response.status_code} with error: {response.text}"
                }
            
            result = response.json()
            
            # Extract plan text
            plan_text = ""
            try:
                plan_text = result['choices'][0]['message']['content']
            except (KeyError, IndexError):
                # Fallback extraction logic
                if "content" in result and isinstance(result["content"], list):
                    for block in result["content"]:
                        if block.get("type") == "text":
                            plan_text += block.get("text", "")
            
            if not plan_text or len(plan_text) < 100:
                raise ValueError("Empty or too short response from API")
            
            return {
                "success": True,
                "plan": plan_text,
                "error": None
            }
            
        except Exception as e:
            st.error(f"❌ Error generating plan: {str(e)}")
            return {
                "success": False,
                "plan": self._generate_fallback_plan(user_profile, day_name, workout_category),
                "error": str(e)
            }
    
    # INDENTATION FIX: This method is now correctly aligned with the class methods above.
    def _generate_fallback_plan(self, user_profile: Dict, day_name: str, workout_category: str) -> str:
        """Generate simple fallback plan"""
        
        # Adjust fallback sets/reps based on goal for better alignment even in error
        goal = user_profile.get("primary_goal", "General Fitness")
        target_sets = self.goal_programming_guidelines.get(goal, {}).get('sets', '3')
        target_reps = self.goal_programming_guidelines.get(goal, {}).get('rep_range', '12')
        target_rest = self.goal_programming_guidelines.get(goal, {}).get('rest', '60 seconds')
        
        # Determine the Focus for the workout
        focus_map = {"Monday": "Lower Focus", "Wednesday": "Upper Focus", "Friday": "Core Focus"}
        day_focus = focus_map.get(day_name, "Balanced Focus")

        return f"""{day_name} – {workout_category} ({day_focus}) Focus

**⚠️ This is a fallback plan. API generation failed. Please see error message above.**

Warm-Up (5-7 minutes)

Seated Marching – [Purpose: Light cardio] – [Duration: 2 minutes] – [Safety Note: Keep movements slow]

Shoulder Rolls – [Purpose: Warm shoulders] – [Duration: 1 minute] – [Safety Note: Controlled motion]

Main Workout (Target: {workout_category} ({day_focus}))

Seated Band Rows
Benefit: [Targets back muscles and supports general fitness]

How to Perform:
1. Sit on a chair, band looped around feet.
2. Pull band towards torso, squeezing shoulder blades.
3. Release and repeat.

Sets: **{target_sets}**

Reps: **{target_reps}**

Intensity: **RPE 4-6**

Rest: **{target_rest}**

Equipment: Resistance Band

Safety Cue: Keep back straight.

Wall Push-ups
Benefit: [Targets chest and arms and supports general fitness]

How to Perform:
1. Stand arm's length from wall, hands shoulder height.
2. Bend elbows, lean in.
3. Push back to start.

Sets: **{target_sets}**

Reps: **{target_reps}**

Intensity: **RPE 4-6**

Rest: **{target_rest}**

Equipment: Wall

Safety Cue: Keep body straight.

Cool-Down (5-7 minutes)

Seated Hamstring Stretch – [Target: Hamstrings] – [60-90 seconds] – [Safety Note: Keep back straight]

Seated Chest Stretch – [Target: Chest] – [60-90 seconds] – [Safety Note: Relax shoulders]
"""

# ============ CUSTOM CSS ============
def inject_custom_css():
    """Inject custom CSS"""
    st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    .header-container {
        background: black;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# ============ SESSION STATE ============
def initialize_session_state():
    """Initialize session state"""
    if 'fitness_plan_generated' not in st.session_state:
        st.session_state.fitness_plan_generated = False
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = {}
    if 'workout_plans' not in st.session_state:
        st.session_state.workout_plans = {}
    if 'generation_in_progress' not in st.session_state:
        st.session_state.generation_in_progress = False
    if 'form_submitted_and_validated' not in st.session_state:
        st.session_state.form_submitted_and_validated = False
    # NEW: State for storing the generated LLM prompts
    if 'all_prompts' not in st.session_state:
        st.session_state.all_prompts = {}

# ============ MAIN APPLICATION ============
# ============ MAIN APPLICATION ============
def main():
    """Main application"""
    
    inject_custom_css()
    initialize_session_state()
    advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)
    
    # Header
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">💪 FriskaAI Fitness Coach</h1>
        <p class="header-subtitle">AI-Powered Personalized Fitness Plans</p>
    </div>
    """, unsafe_allow_html=True)
    
    # MAIN FORM
    if not st.session_state.fitness_plan_generated and not st.session_state.generation_in_progress:
        # ... (Your form code remains here - only form inputs) ...
        # (The form submission logic remains as is, setting st.session_state.generation_in_progress = True and st.rerun())
        
        with st.form("fitness_form"):
            
            # Basic Info
            st.subheader("📋 Basic Information")
            col1, col2 = st.columns(2)
            
            # --- Form Inputs ---
            with col1:
                name = st.text_input("Name *", placeholder="Your name", key="name_input")
                age = st.number_input("Age *", min_value=13, max_value=100, value=30, key="age_input")
                gender = st.selectbox("Gender *", ["Male", "Female", "Other"], key="gender_input")
            
            with col2:
                unit_system = st.radio("Units *", ["Metric (kg, cm)", "Imperial (lbs, in)"], key="unit_input")
                
                weight_kg = 0.0
                height_cm = 0.0
                if unit_system == "Metric (kg, cm)":
                    weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=70.0, key="weight_kg_input")
                    height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=170.0, key="height_cm_input")
                else:
                    weight_lbs = st.number_input("Weight (lbs) *", min_value=66.0, max_value=660.0, value=154.0, key="weight_lbs_input")
                    height_in = st.number_input("Height (in) *", min_value=39.0, max_value=98.0, value=67.0, key="height_in_input")
                    weight_kg = weight_lbs * 0.453592
                    height_cm = height_in * 2.54
            
            # BMI calculation
            bmi = 0
            if weight_kg > 0 and height_cm > 0:
                bmi = weight_kg / ((height_cm / 100) ** 2)
                st.info(f"📊 Your BMI: {bmi:.1f}")
            
            # Goals
            st.subheader("🎯 Fitness Goals")
            col1, col2 = st.columns(2)
            
            with col1:
                primary_goal = st.selectbox(
                    "Primary Goal *",
                    list(advisor.goal_programming_guidelines.keys()), key="primary_goal_input"
                )
            
            with col2:
                secondary_goal = st.selectbox(
                    "Secondary Goal (Optional)",
                    ["None"] + list(advisor.goal_programming_guidelines.keys()), key="secondary_goal_input"
                )
            
            # Fitness Level
            fitness_level = st.selectbox(
                "Fitness Level *",
                list(FITNESS_LEVELS.keys()), key="fitness_level_input"
            )
            
            # Show level description
            level_info = FITNESS_LEVELS[fitness_level]
            st.info(f"**{fitness_level}**: {level_info['description']} | RPE: {level_info['rpe_range']}")
            
            # Medical Conditions
            st.subheader("🏥 Health Screening")
            medical_conditions = st.multiselect(
                "Medical Conditions *",
                MEDICAL_CONDITIONS,
                default=["None"], key="medical_conditions_input"
            )
            
            # Physical Limitations
            st.warning("⚠️ **Physical Limitations** - Describe ANY injuries, pain, or movement restrictions")
            physical_limitations = st.text_area(
                "Physical Limitations (Important for Safety) *",
                placeholder="E.g., 'Previous right knee surgery - avoid deep squats'",
                height=100, key="physical_limitations_input"
            )
            
            # Training Schedule
            st.subheader("💪 Training Schedule")
            col1, col2 = st.columns(2)
            
            with col1:
                days_per_week = st.multiselect(
                    "Training Days *",
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    default=["Monday", "Wednesday", "Friday"], key="days_per_week_input"
                )
            
            with col2:
                session_duration = st.selectbox(
                    "Session Duration *",
                    ["15-20 minutes", "20-30 minutes", "30-45 minutes", "45-60 minutes"], key="session_duration_input"
                )
            
            # Equipment (Simplified to prevent massive key list)
            st.subheader("🏋️ Available Equipment")
            eq_options = ["Bodyweight Only", "Dumbbells", "Resistance Bands", "Kettlebells", "Barbell", "Bench", "Pull-up Bar", "Yoga Mat", "Machines"]
            equipment = st.multiselect("Select all available equipment:", eq_options, default=["Bodyweight Only"], key="equipment_input")

            if not equipment:
                equipment = ["Bodyweight Only"]
            
            # FIXED: Submit button inside form
            st.markdown("---")
            submit_clicked = st.form_submit_button(
                "🚀 Generate My Fitness Plan",
                use_container_width=True,
                type="primary"
            )
            
            # Process ONLY when button clicked
            if submit_clicked:
                # Validation: Check mandatory fields
                if not name or len(name.strip()) < 2:
                    st.error("❌ Please enter your name.")
                elif not days_per_week:
                    st.error("❌ Please select at least one training day.")
                elif bmi <= 0 or (weight_kg <= 0 or height_cm <= 0):
                    st.error("❌ Please ensure valid weight and height inputs.")
                else:
                    # Store profile and set flag to start generation
                    st.session_state.user_profile = {
                        "name": name.strip(),
                        "age": age,
                        "gender": gender,
                        "weight_kg": weight_kg,
                        "height_cm": height_cm,
                        "bmi": round(bmi, 1) if bmi > 0 else 0,
                        "primary_goal": primary_goal,
                        "secondary_goal": secondary_goal,
                        "fitness_level": fitness_level,
                        "medical_conditions": medical_conditions,
                        "physical_limitations": physical_limitations.strip(),
                        "days_per_week": days_per_week,
                        "session_duration": session_duration,
                        "available_equipment": equipment
                    }
                    
                    st.session_state.workout_plans = {} 
                    st.session_state.all_prompts = {} # CLEAR PROMPTS
                    st.session_state.generation_in_progress = True
                    st.rerun() # Rerun once to start generation outside the form

    # =================================================================================
    # GENERATION BLOCK (Only runs when st.session_state.generation_in_progress is True)
    # This block executes fully and then reruns to the display state.
    # =================================================================================
    if st.session_state.generation_in_progress:
        st.subheader("🔄 Generating your personalized fitness plan...")
        
        # PROMPT DISPLAY SECTION - Display ALL prompts generated so far
        st.markdown("---")
        st.subheader("💡 LLM Prompts for Accuracy Testing")
        st.info("The text below is the *exact* prompt sent to the Mistral LLM for each day as it's generated.")
        
        # Prepare components
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        profile = st.session_state.user_profile
        
        # The prompt container is crucial for live updates
        prompt_container = st.container()

        # Iterate through days and generate
        for idx, day in enumerate(profile['days_per_week']):
            
            # CRITICAL: Pass only the plans generated *before* the current day
            previous_plans_to_pass = {d: st.session_state.workout_plans[d] for d in profile['days_per_week'] if d in st.session_state.workout_plans and profile['days_per_week'].index(d) < idx}
            
            # --- PROMPT GENERATION (FOR DISPLAY & API) ---
            system_prompt = advisor._build_system_prompt(
                profile, 
                day, 
                idx, 
                previous_plans_to_pass, 
                "Full Body"
            )
            
            # Store the prompt for display
            st.session_state.all_prompts[day] = system_prompt
            
            # Display the prompt for the current day inside the container
            with prompt_container:
                with st.expander(f"Prompt for **{day}** (Click to view)", expanded=False):
                    st.code(system_prompt, language='markdown')

            # --- API CALL ---
            progress = (idx) / len(profile['days_per_week']) 
            if progress == 0 and idx == 0:
                 progress = 0.01
            progress_bar.progress(progress)
            status_text.text(f"Generating {day} workout... ({idx + 1}/{len(profile['days_per_week'])})")
            
            result = advisor.generate_workout_plan(
                profile,
                day,
                idx,
                previous_plans_to_pass, 
                "Full Body"
            )
            
            # Update session state with the result for the current day
            st.session_state.workout_plans[day] = result
            
            # Update progress bar to show generation *complete* for this day
            progress_bar.progress((idx + 1) / len(profile['days_per_week']))


        progress_bar.empty()
        status_text.empty()
        
        # Final status check and transition
        all_success = all(
            st.session_state.workout_plans[day]['success'] 
            for day in profile['days_per_week']
        )
        
        if all_success:
            st.success("✅ Your fitness plan is ready! See the generated plan and the prompts below.")
        else:
            st.error("⚠️ Plan generation complete, but one or more days failed (used fallback). Check the API key and error messages in the console.")
        
        # Set final flags and rerun to the display state
        st.session_state.fitness_plan_generated = True
        st.session_state.generation_in_progress = False
        st.rerun() 
        # The script will now exit this block and move to the 'DISPLAY PLANS' block.
    # =================================================================================
    
    # DISPLAY PLANS
    # ... (Rest of your code for displaying plans remains here) ...
    # (Removed for brevity in this response, but keep it in your file)
    else:
        profile = st.session_state.user_profile
        
        # --- Top Section ---
        st.markdown(f"👋 Welcome, **{profile['name']}**!")
        st.markdown(f"Your Personalized Fitness Plan is Ready")
        st.markdown(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 🎯 Goal: **{profile['primary_goal']}** | 💪 Level: **{profile['fitness_level']}**")
        
        st.markdown("\n") # Add newline for spacing
        
        # Show physical limitations if present
        if profile.get('physical_limitations'):
            st.warning(f"⚠️ **Accommodated Limitations:** {profile['physical_limitations']}")
        
        st.markdown("---")
        
        # DEBUGGING PROMPT SECTION (Show on result page as well)
        if st.session_state.all_prompts:
            st.markdown("## ⚙️ Debugging: LLM Prompts (For Testing)")
            with st.expander("Show Generated LLM Prompts", expanded=False):
                for day, prompt in st.session_state.all_prompts.items():
                    st.markdown(f"### Prompt for {day}")
                    st.code(prompt, language='markdown')
            st.markdown("---")
        
        # Display plans
        st.markdown("## 📅 Your Weekly Workout Schedule")
        
        for idx, day in enumerate(profile['days_per_week']):
            with st.expander(f"📋 {day} Workout", expanded=True if idx == 0 else False):
                if day in st.session_state.workout_plans:
                    plan_data = st.session_state.workout_plans[day]
                    
                    if plan_data['success']:
                        st.markdown(plan_data['plan'])
                    else:
                        st.error(f"⚠️ API Error: {plan_data.get('error', 'Unknown error')}. Showing fallback plan.")
                        st.markdown(plan_data['plan'])  # Show fallback
                else:
                    st.warning("Plan not available")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Generate New Plan", use_container_width=True):
                st.session_state.fitness_plan_generated = False
                st.session_state.workout_plans = {}
                st.session_state.user_profile = {}
                st.session_state.all_prompts = {} # Clear prompts on restart
                st.rerun()
        
        with col2:
            # Download preparation for a button
            markdown_content = generate_markdown_export(
                profile, 
                st.session_state.workout_plans
            )
            st.download_button(
                label="📥 Download Plan",
                data=markdown_content,
                file_name=f"FriskaAI_Plan_{profile['name']}_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with col3:
            if st.button("📊 View Profile", use_container_width=True):
                display_profile_summary(profile)
        
        # Additional Resources
        st.markdown("---")
        st.markdown("## 📚 Additional Resources")
        
        with st.expander("💡 Training Tips"):
            st.markdown("""
            **Maximizing Your Workout:**
            - **Warm-up is mandatory** - Never skip the warm-up to prevent injuries
            - **RPE Guide**: 
              - 3-4: Very light, can talk easily
              - 5-6: Moderate, breathing harder but can hold conversation
              - 7-8: Hard, difficult to talk
              - 9-10: Maximum effort
            - **Progressive Overload**: Gradually increase difficulty week by week
            - **Recovery**: Rest days are when muscles grow stronger
            - **Hydration**: Drink water before, during, and after workouts
            - **Form > Weight**: Perfect technique prevents injuries
            """)
        
        with st.expander("🍎 Nutrition Guidelines"):
            st.markdown(f"""
            **Based on your goal: {profile['primary_goal']}**
            
            {get_nutrition_guidelines(profile['primary_goal'])}
            
            **General Tips:**
            - Stay hydrated (8-10 glasses of water daily)
            - Eat protein within 2 hours post-workout
            - Balance macros: Protein, Carbs, Healthy Fats
            - Avoid processed foods and excessive sugar
            """)
        
        with st.expander("⚠️ Safety Warnings"):
            st.markdown("""
            **STOP EXERCISING if you experience:**
            - Chest pain or pressure
            - Severe shortness of breath
            - Dizziness or lightheadedness
            - Unusual fatigue
            - Sharp joint pain
            - Numbness or tingling
            
            **Important Notes:**
            - This plan is AI-generated guidance, NOT medical advice
            - Consult your doctor before starting any exercise program
            - Listen to your body and modify as needed
            - Keep emergency contacts readily available
            """)
        
        # FAQ Section
        display_faq()

def generate_markdown_export(profile: Dict, workout_plans: Dict) -> str:
    """Generate markdown file for download"""
    
    md_content = f"""# FriskaAI Fitness Plan
## Generated on {datetime.now().strftime('%B %d, %Y')}

---

## 👤 Profile Summary

**Name:** {profile['name']}
**Age:** {profile['age']} | **Gender:** {profile['gender']} | **BMI:** {profile['bmi']}

**Primary Goal:** {profile['primary_goal']}
**Secondary Goal:** {profile.get('secondary_goal', 'None')}

**Fitness Level:** {profile['fitness_level']}
**Training Days:** {', '.join(profile['days_per_week'])}
**Session Duration:** {profile['session_duration']}

**Medical Conditions:** {', '.join(profile.get('medical_conditions', ['None']))}
**Physical Limitations:** {profile.get('physical_limitations', 'None')}

**Available Equipment:** {', '.join(profile.get('available_equipment', ['Bodyweight Only']))}

---

"""
    
    # Add each workout day
    for day in profile['days_per_week']:
        if day in workout_plans and workout_plans[day]['plan']:
             # Check if plan was success or fallback
            status = "✅ SUCCESS" if workout_plans[day]['success'] else "⚠️ FALLBACK PLAN (API Error)"
            md_content += f"\n## {day} Workout - {status}\n\n"
            md_content += f"{workout_plans[day]['plan']}\n\n---\n"
    
    # Add footer
    md_content += """

## ⚠️ Important Disclaimers

1. This workout plan is AI-generated guidance and is NOT a substitute for professional medical advice
2. Consult your physician before starting any new exercise program
3. Stop exercising immediately if you experience pain, dizziness, or unusual symptoms
4. Modify exercises as needed based on how you feel
5. Results may vary based on consistency, nutrition, and individual factors

## 📞 Emergency Contacts

Always keep emergency contacts available during workouts.

---

**Generated by FriskaAI Fitness Coach**
*Powered by AI*
"""
    
    return md_content

def display_profile_summary(profile: Dict):
    """Display user profile in modal-style"""
    st.markdown("### 👤 Your Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **Personal Info:**
        - Name: {profile['name']}
        - Age: {profile['age']}
        - Gender: {profile['gender']}
        - BMI: {profile['bmi']}
        """)
        
        st.markdown(f"""
        **Goals:**
        - Primary: {profile['primary_goal']}
        - Secondary: {profile.get('secondary_goal', 'None')}
        """)
    
    with col2:
        st.markdown(f"""
        **Fitness Level:**
        - {profile['fitness_level']}
        
        **Schedule:**
        - Days: {', '.join(profile['days_per_week'])}
        - Duration: {profile['session_duration']}
        """)
        
        st.markdown(f"""
        **Equipment:**
        - {', '.join(profile.get('available_equipment', ['None']))}
        """)
    
    if profile.get('medical_conditions') and profile['medical_conditions'] != ['None']:
        st.warning(f"**Medical Conditions:** {', '.join(profile['medical_conditions'])}")
    
    if profile.get('physical_limitations'):
        st.warning(f"**Physical Limitations:** {profile['physical_limitations']}")

def get_nutrition_guidelines(goal: str) -> str:
    """Get nutrition guidelines based on goal"""
    
    guidelines = {
        "Weight Loss": """
        - **Calorie Deficit**: Consume 300-500 calories below maintenance
        - **Protein**: 1.6-2.2g per kg bodyweight (preserves muscle)
        - **Carbs**: Moderate (prioritize around workouts)
        - **Fats**: 0.8-1g per kg bodyweight
        - **Meal Timing**: Eat protein with each meal
        """,
        "Muscle Gain": """
        - **Calorie Surplus**: Consume 200-400 calories above maintenance
        - **Protein**: 1.8-2.4g per kg bodyweight
        - **Carbs**: High (fuel for training and recovery)
        - **Fats**: 0.8-1.2g per kg bodyweight
        - **Post-Workout**: Protein + Carbs within 2 hours
        """,
        "Increase Overall Strength": """
        - **Balanced Calories**: Slight surplus or maintenance
        - **Protein**: 1.8-2.2g per kg bodyweight
        - **Carbs**: Moderate to high (power fuel)
        - **Pre-Workout**: Carbs for energy
        - **Recovery**: Focus on protein and sleep
        """,
        "Improve Cardiovascular Fitness": """
        - **Balanced Diet**: Maintenance calories
        - **Carbs**: Moderate to high (endurance fuel)
        - **Hydration**: Critical for performance
        - **Electrolytes**: Important for longer sessions
        - **Timing**: Light meal 2-3 hours before cardio
        """,
        "Rehabilitation & Injury Prevention": """
        - **Anti-Inflammatory Foods**: Omega-3s, berries, leafy greens
        - **Protein**: 1.6-2.0g per kg (tissue repair)
        - **Vitamin D & Calcium**: Bone health
        - **Collagen**: Consider supplementation
        - **Hydration**: Essential for joint health
        """
    }
    
    return guidelines.get(goal, """
    - **Balanced Approach**: Maintenance calories
    - **Protein**: 1.6-2.0g per kg bodyweight
    - **Carbs & Fats**: Balanced based on activity level
    - **Whole Foods**: Prioritize unprocessed options
    - **Consistency**: Key to long-term results
    """)

def display_faq():
    """Display FAQ section"""
    st.markdown("---")
    st.markdown("## ❓ Frequently Asked Questions")
    
    faq_items = {
        "How often should I update my fitness level?": """
        Reassess every 4-6 weeks. Signs you've progressed:
        - Exercises feel easier at same intensity
        - Can complete more reps/longer duration
        - Recovery time has decreased
        - No longer experiencing muscle soreness
        """,
        
        "What if I miss a workout?": """
        Don't panic! Here's what to do:
        - **Missed 1 day**: Continue with next scheduled workout
        - **Missed 2-3 days**: Resume at lower intensity (80%)
        - **Missed >1 week**: Consider restarting at previous fitness level
        - Never "double up" to make up for missed sessions
        """,
        
        "Can I do the workouts at home?": """
        Absolutely! If you selected "Bodyweight Only" equipment, all exercises are home-friendly. 
        You can also modify equipment-based exercises with household items:
        - Dumbbells → Water bottles, books
        - Resistance bands → Towels
        - Bench → Sturdy chair or stairs
        """,
        
        "How long until I see results?": """
        Timeline varies by goal:
        - **Strength**: 2-4 weeks (neural adaptations)
        - **Muscle Growth**: 6-8 weeks (visible changes)
        - **Weight Loss**: 4-8 weeks (1-2 lbs/week is healthy)
        - **Cardiovascular**: 3-6 weeks (improved endurance)
        - **Flexibility**: 2-4 weeks (increased ROM)
        
        Consistency is key!
        """,
        
        "What if an exercise hurts?": """
        **STOP IMMEDIATELY.** Pain is your body's warning signal.
        
        Then:
        1. Assess: Sharp pain vs. muscle fatigue?
        2. Modify: Use easier variation or skip exercise
        3. Rest: Allow 24-48 hours recovery
        4. Consult: See healthcare provider if pain persists
        
        Remember: "No pain, no gain" is a MYTH. Quality > Quantity.
        """,
        
        "Do I need supplements?": """
        Not required, but can help:
        - **Protein Powder**: Convenient protein source (if struggling to meet needs)
        - **Creatine**: Evidence-based for strength (5g/day)
        - **Vitamin D**: If deficient or low sunlight exposure
        - **Omega-3**: Anti-inflammatory benefits
        
        ⚠️ ALWAYS consult doctor before starting supplements, especially with medical conditions.
        """,
        
        "Can I combine this with other activities?": """
        Yes! This plan complements:
        - Walking/hiking
        - Swimming
        - Cycling
        - Sports (tennis, basketball, etc.)
        
        Just monitor total volume and ensure adequate recovery.
        """,
        
        "What about nutrition tracking?": """
        While not mandatory, tracking can help:
        - **Apps**: MyFitnessPal, Cronometer, MacroFactor
        - **Focus**: Protein intake and overall calories
        - **Don't obsess**: Consistency > perfection
        
        Start with tracking for 1-2 weeks to understand your baseline.
        """
    }
    
    for question, answer in faq_items.items():
        with st.expander(f"❔ {question}"):
            st.markdown(answer)

# ============ FOOTER ============
def display_footer():
    """Display footer with disclaimers"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <h3>⚠️ Medical Disclaimer</h3>
        <p>
        <strong>This fitness plan is AI-generated guidance and NOT medical advice.</strong><br>
        Always consult with a qualified healthcare provider before starting any exercise program,<br>
        especially if you have pre-existing medical conditions or physical limitations.
        </p>
        <p>
        <strong>FriskaAI and its creators are not liable for any injuries or health complications<br>
        arising from the use of these workout plans.</strong>
        </p>
        <hr style='margin: 2rem 0;'>
        <p style='font-size: 0.9em;'>
        💪 <strong>FriskaAI Fitness Coach</strong> | Powered by AI<br>
        © 2025 | For educational and informational purposes only
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============ RUN APPLICATION ============
if __name__ == "__main__": 
    main()
    display_footer()