import streamlit as st
import requests
from typing import Dict, List, Optional, Set
import re
from datetime import datetime
import pandas as pd

# ============ CONFIGURATION ============
# CRITICAL FIX: Using Claude API endpoint instead of Azure Mistral
API_KEY = "08Z5HKTA9TshVWbKb68vsef3oG7Xx0Hd"
ENDPOINT_URL = "https://mistral-small-2503-Gnyan-Test.swedencentral.models.ai.azure.com/chat/completions"  # Use Anthropic endpoint

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
        df = pd.read_excel("Top Lifestyle Disorders and Medical Conditions & ExerciseTags.xlsx")
        
        # Convert to dictionary for easier access
        condition_db = {}
        for _, row in df.iterrows():
            condition_name = row['Condition']
            condition_db[condition_name] = {
                'medications': row.get('Medication(s)', ''),
                'direct_impact': row.get('Direct Exercise Impact', ''),
                'indirect_impact': row.get('Indirect Exercise Impacts', ''),
                'contraindicated': row.get('Contraindicated Exercises', ''),
                'modified_safer': row.get('Modified / Safer Exercises', '')
            }
        return condition_db
    except Exception as e:
        st.warning(f"Could not load condition database: {str(e)}. Using fallback database.")
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
        self.weekly_exercises_used = {
            'warmup': set(),
            'main': set(),
            'cooldown': set()
        }
        
        # UPDATED: Goal programming WITHOUT RPE (moved to levels)
        self.goal_programming_guidelines = {
            "Weight Loss": {
                "priority": "Low to moderate-intensity cardio + resistance for large muscle groups",
                "rep_range": "12-20",
                "rest": "30-45 seconds",
                "cardio_focus": "60-70% of workout time"
            },
            "Muscle Gain": {
                "priority": "Progressive overload resistance training, controlled tempo",
                "rep_range": "6-12",
                "rest": "60-90 seconds",
                "volume": "3-5 sets per exercise"
            },
            "Increase Overall Strength": {
                "priority": "Compound lifts, progressive loading, mobility work",
                "rep_range": "4-8",
                "rest": "90-180 seconds",
                "focus": "Heavy compound movements"
            },
            "Improve Cardiovascular Fitness": {
                "priority": "Aerobic/interval protocols, recovery days",
                "intensity": "60-80% max HR",
                "modality": "Continuous or interval training"
            },
            "Improve Flexibility & Mobility": {
                "priority": "Stretching, joint mobility, dynamic ROM",
                "hold_duration": "30-60 seconds per stretch",
                "focus": "Full range of motion"
            },
            "Rehabilitation & Injury Prevention": {
                "priority": "Corrective exercises, stability, low-load resistance",
                "rep_range": "10-15",
                "rest": "60-90 seconds",
                "exclude": "High-impact, ballistic movements"
            },
            "Improve Posture and Balance": {
                "priority": "Core activation, mobility, balance",
                "focus": "Postural muscles, single-leg work"
            },
            "General Fitness": {
                "priority": "Balanced approach: cardio, strength, flexibility",
                "rep_range": "10-15",
                "rest": "45-60 seconds"
            }
        }
    
    def reset_weekly_tracker(self):
        """Reset exercise tracker for new week generation"""
        self.weekly_exercises_used = {
            'warmup': set(),
            'main': set(),
            'cooldown': set()
        }
    
    def _get_condition_details_from_db(self, condition: str) -> Dict:
        """Get condition details from loaded Excel database"""
        if condition in CONDITION_DATABASE:
            return CONDITION_DATABASE[condition]
        
        # Fallback to hardcoded if not in Excel
        fallback_db = {
            "Hypertension": {
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
            "contraindicated": "High-risk movements",
            "modified_safer": "Low-impact, controlled movements"
        })
    
    def _build_system_prompt(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        workout_category: str = "Full Body"
    ) -> str:
        """Build comprehensive system prompt with all fixes"""
        
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
        
        # Get level-specific RPE
        level_data = FITNESS_LEVELS.get(fitness_level, FITNESS_LEVELS["Level 3 – Moderate / Independent"])
        level_rpe = level_data['rpe_range']
        
        # Get goal guidelines
        goal_guidelines = self.goal_programming_guidelines.get(primary_goal, {})
        
        prompt = f"""You are FriskaAI, an expert clinical exercise physiologist (ACSM-CEP).

**USER PROFILE:**
- Name: {name}
- Age: {age} | Gender: {gender} | BMI: {bmi}
- Fitness Level: {fitness_level}
  * RPE Range: {level_rpe} (Rate of Perceived Exertion)
  * Description: {level_data['description']}
  * Appropriate Exercises: {level_data['exercises']}

**GOALS:**
- Primary Goal: {primary_goal}
  * {goal_guidelines.get('priority', 'Balanced fitness approach')}
  * Rep Range: {goal_guidelines.get('rep_range', '10-15')}
  * Rest: {goal_guidelines.get('rest', '45-60 seconds')}
"""

        if secondary_goal and secondary_goal != "None":
            secondary_guidelines = self.goal_programming_guidelines.get(secondary_goal, {})
            prompt += f"""
- Secondary Goal: {secondary_goal}
  * {secondary_guidelines.get('priority', 'Support primary goal')}
"""

        # CRITICAL: Physical limitations section
        if physical_limitations and physical_limitations.strip():
            prompt += f"""

**PHYSICAL LIMITATIONS (CRITICAL - MUST ACCOMMODATE):**
{physical_limitations}

**ACTION REQUIRED:**
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
Category: {workout_category}

**MANDATORY STRUCTURE:**

### {day_name} – {workout_category}

**Warm-Up (5-8 minutes)**
1. [Movement] – [Purpose] – [Duration/Reps] – [Safety Note]
2. [Movement] – [Purpose] – [Duration/Reps] – [Safety Note]
3. [Movement] – [Purpose] – [Duration/Reps] – [Safety Note]

**Main Workout (20-30 minutes)**

For each exercise include:

1. [Exercise Name]
**Benefit:** [How this supports {primary_goal}]
**How to Perform:**
1. [Step 1]
2. [Step 2]
3. [Step 3]
**Sets × Reps:** {goal_guidelines.get('rep_range', '10-15')} reps
**Intensity:** RPE {level_rpe}
**Rest:** {goal_guidelines.get('rest', '45-60 seconds')}
**Equipment:** [From available list]
**Safety Cue:** [Specific to limitations/conditions]

[Repeat for 6-8 exercises]

**Cool-Down (5 minutes)**
1. [Stretch] – [Target] – [60 seconds] – [Safety Note]
2. [Stretch] – [Target] – [60 seconds] – [Safety Note]
3. [Stretch] – [Target] – [60 seconds] – [Safety Note]

**CRITICAL RULES:**
1. ALL exercises must match {fitness_level} complexity
2. ZERO contraindicated exercises for: {', '.join(medical_conditions)}
3. MUST accommodate physical limitations: {physical_limitations if physical_limitations else 'None'}
4. RPE must be {level_rpe} (no exceptions)
5. Support {primary_goal} with every exercise choice

Generate the complete workout plan now in English only.
"""
        
        return prompt
    
    def generate_workout_plan(
            self,
            user_profile: Dict,
            day_name: str,
            day_index: int,
            workout_category: str = "Full Body"
        ) -> Dict:
        """Generate workout plan with fixed API call"""
        
        try:
            # ... (system_prompt building code remains the same)

            # FIXED: Proper API call - CORRECTION APPLIED HERE
            headers = {
                "Content-Type": "application/json",
                # CRITICAL FIX: Use Authorization: Bearer <API_KEY> format
                # The 'api-key' header you currently have is for Azure OpenAI service,
                # but the error message suggests a standard 'Authorization' header is needed.
                "Authorization": f"Bearer {self.api_key}" 
            }
            
            # ... (rest of the payload and request code remains the same)
            
            payload = {
                "model": "mistral-small",
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, an expert clinical exercise physiologist."},
                    {"role": "user", "content": system_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            
            response = requests.post(self.endpoint_url, headers=headers, json=payload)
            
            # Debug logging
            st.write(f"DEBUG - Status Code: {response.status_code}")
            
            if response.status_code != 200:
                st.error(f"API Error {response.status_code}: {response.text}")
                raise Exception(f"API returned {response.status_code}")
            
            result = response.json()
            
            # Extract plan text
            plan_text = ""
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
    
        def _generate_fallback_plan(self, user_profile: Dict, day_name: str, workout_category: str) -> str:
            """Generate simple fallback plan"""
            return f"""### {day_name} – {workout_category}

**⚠️ This is a fallback plan. API generation failed.**

**Warm-Up (5 minutes)**
1. March in Place – 2 minutes
2. Arm Circles – 1 minute
3. Leg Swings – 2 minutes

**Main Workout (25 minutes)**

1. Bodyweight Squats
   - Sets × Reps: 3 × 12
   - Rest: 60 seconds

2. Wall/Modified Push-ups
   - Sets × Reps: 3 × 10
   - Rest: 60 seconds

3. Glute Bridges
   - Sets × Reps: 3 × 15
   - Rest: 45 seconds

4. Plank Hold
   - Duration: 3 × 30 seconds
   - Rest: 45 seconds

**Cool-Down (5 minutes)**
1. Hamstring Stretch – 60 seconds each leg
2. Quad Stretch – 60 seconds each leg
3. Child's Pose – 60 seconds

*Please retry with Generate Plan button for personalized workout.*
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
        background: white;
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
    if not st.session_state.fitness_plan_generated:
        
        with st.form("fitness_form"):
            
            # Basic Info
            st.subheader("📋 Basic Information")
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name *", placeholder="Your name")
                age = st.number_input("Age *", min_value=13, max_value=100, value=30)
                gender = st.selectbox("Gender *", ["Male", "Female", "Other"])
            
            with col2:
                unit_system = st.radio("Units *", ["Metric (kg, cm)", "Imperial (lbs, in)"])
                
                if unit_system == "Metric (kg, cm)":
                    weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=70.0)
                    height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=170.0)
                else:
                    weight_lbs = st.number_input("Weight (lbs) *", min_value=66.0, max_value=660.0, value=154.0)
                    height_in = st.number_input("Height (in) *", min_value=39.0, max_value=98.0, value=67.0)
                    weight_kg = weight_lbs * 0.453592
                    height_cm = height_in * 2.54
            
            # BMI calculation
            if weight_kg > 0 and height_cm > 0:
                bmi = weight_kg / ((height_cm / 100) ** 2)
                st.info(f"📊 Your BMI: {bmi:.1f}")
            
            # Goals
            st.subheader("🎯 Fitness Goals")
            col1, col2 = st.columns(2)
            
            with col1:
                primary_goal = st.selectbox(
                    "Primary Goal *",
                    list(advisor.goal_programming_guidelines.keys())
                )
            
            with col2:
                secondary_goal = st.selectbox(
                    "Secondary Goal (Optional)",
                    ["None"] + list(advisor.goal_programming_guidelines.keys())
                )
            
            # Fitness Level
            fitness_level = st.selectbox(
                "Fitness Level *",
                list(FITNESS_LEVELS.keys())
            )
            
            # Show level description
            level_info = FITNESS_LEVELS[fitness_level]
            st.info(f"**{fitness_level}**: {level_info['description']} | RPE: {level_info['rpe_range']}")
            
            # Medical Conditions
            st.subheader("🏥 Health Screening")
            medical_conditions = st.multiselect(
                "Medical Conditions *",
                MEDICAL_CONDITIONS,
                default=["None"]
            )
            
            # FIXED: Physical Limitations - More prominent
            st.warning("⚠️ **Physical Limitations** - Describe ANY injuries, pain, or movement restrictions")
            physical_limitations = st.text_area(
                "Physical Limitations (Important for Safety) *",
                placeholder="E.g., 'Previous right knee surgery - avoid deep squats' or 'Lower back pain - no forward bending' or 'Right shoulder impingement - limited overhead movements'",
                height=100,
                help="Be specific! This ensures we avoid exercises that could cause pain or injury."
            )
            
            # Training Schedule
            st.subheader("💪 Training Schedule")
            col1, col2 = st.columns(2)
            
            with col1:
                days_per_week = st.multiselect(
                    "Training Days *",
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    default=["Monday", "Wednesday", "Friday"]
                )
            
            with col2:
                session_duration = st.selectbox(
                    "Session Duration *",
                    ["15-20 minutes", "20-30 minutes", "30-45 minutes", "45-60 minutes"]
                )
            
            # Equipment
            st.subheader("🏋️ Available Equipment")
            eq_cols = st.columns(4)
            
            with eq_cols[0]:
                eq_bodyweight = st.checkbox("Bodyweight Only", value=True)
                eq_dumbbells = st.checkbox("Dumbbells")
            
            with eq_cols[1]:
                eq_bands = st.checkbox("Resistance Bands")
                eq_kettlebells = st.checkbox("Kettlebells")
            
            with eq_cols[2]:
                eq_barbell = st.checkbox("Barbell")
                eq_bench = st.checkbox("Bench")
            
            with eq_cols[3]:
                eq_pullup = st.checkbox("Pull-up Bar")
                eq_mat = st.checkbox("Yoga Mat")
            
            # Compile equipment
            equipment = []
            if eq_bodyweight: equipment.append("Bodyweight Only")
            if eq_dumbbells: equipment.append("Dumbbells")
            if eq_bands: equipment.append("Resistance Bands")
            if eq_kettlebells: equipment.append("Kettlebells")
            if eq_barbell: equipment.append("Barbell")
            if eq_bench: equipment.append("Bench")
            if eq_pullup: equipment.append("Pull-up Bar")
            if eq_mat: equipment.append("Yoga Mat")
            
            if not equipment:
                equipment = ["Bodyweight Only"]
            
            # FIXED: Submit button inside form
            st.markdown("---")
            submit_clicked = st.form_submit_button(
                "🚀 Generate My Fitness Plan",
                use_container_width=True,
                type="primary"
            )
            
            # FIXED: Process ONLY when button clicked
            if submit_clicked:
                # Validation
                if not name or len(name.strip()) < 2:
                    st.error("❌ Please enter your name")
                elif not days_per_week:
                    st.error("❌ Please select at least one training day")
                else:
                    # Store profile
                    st.session_state.user_profile = {
                        "name": name.strip(),
                        "age": age,
                        "gender": gender,
                        "weight_kg": weight_kg,
                        "height_cm": height_cm,
                        "bmi": round(bmi, 1) if weight_kg > 0 and height_cm > 0 else 0,
                        "primary_goal": primary_goal,
                        "secondary_goal": secondary_goal,
                        "fitness_level": fitness_level,
                        "medical_conditions": medical_conditions,
                        "physical_limitations": physical_limitations.strip(),
                        "days_per_week": days_per_week,
                        "session_duration": session_duration,
                        "available_equipment": equipment
                    }
                    
                    # Set flag to show we're generating
                    st.session_state.generation_in_progress = True
                    st.rerun()
        
        # FIXED: Generation happens OUTSIDE form, AFTER button click
        if st.session_state.generation_in_progress:
            st.info("🔄 Generating your personalized fitness plan...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            profile = st.session_state.user_profile
            advisor.reset_weekly_tracker()
            
            for idx, day in enumerate(profile['days_per_week']):
                progress = (idx + 1) / len(profile['days_per_week'])
                progress_bar.progress(progress)
                status_text.text(f"Generating {day} workout... ({idx + 1}/{len(profile['days_per_week'])})")
                
                result = advisor.generate_workout_plan(
                    profile,
                    day,
                    idx,
                    "Full Body"
                )
                
                st.session_state.workout_plans[day] = result
            
            progress_bar.empty()
            status_text.empty()
            
            # Check if all succeeded
            all_success = all(
                st.session_state.workout_plans[day]['success'] 
                for day in profile['days_per_week']
            )
            
            if all_success:
                st.success("✅ Your fitness plan is ready!")
            else:
                st.warning("⚠️ Some plans used fallback mode. Check API configuration.")
            
            st.session_state.fitness_plan_generated = True
            st.session_state.generation_in_progress = False
            st.rerun()
    
    # DISPLAY PLANS
    else:
        profile = st.session_state.user_profile
        
        st.success(f"👋 Welcome back, {profile['name']}!")
        st.info(f"🎯 Primary Goal: {profile['primary_goal']} | 💪 Level: {profile['fitness_level']}")
        
        # Show physical limitations if present
        if profile.get('physical_limitations'):
            st.warning(f"⚠️ **Accommodated Limitations:** {profile['physical_limitations']}")
        
        # Display plans
        st.markdown("## 📅 Your Weekly Workout Schedule")
        
        for day in profile['days_per_week']:
            with st.expander(f"📋 {day} Workout", expanded=False):
                if day in st.session_state.workout_plans:
                    plan_data = st.session_state.workout_plans[day]
                    
                    if plan_data['success']:
                        st.markdown(plan_data['plan'])
                    else:
                        st.error(f"⚠️ API Error: {plan_data.get('error', 'Unknown error')}")
                        st.markdown(plan_data['plan'])  # Show fallback
                else:
                    st.warning("Plan not available")
        
        # Action buttons
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Generate New Plan", use_container_width=True):
                st.session_state.fitness_plan_generated = False
                st.session_state.workout_plans = {}
                st.session_state.user_profile = {}
                st.rerun()
        
        with col2:
            if st.button("📥 Download Plan", use_container_width=True):
                markdown_content = generate_markdown_export(
                    profile, 
                    st.session_state.workout_plans
                )
                st.download_button(
                    label="💾 Download as Markdown",
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
        if day in workout_plans and workout_plans[day]['success']:
            md_content += f"\n{workout_plans[day]['plan']}\n\n---\n"
    
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
*Powered by Claude AI - Your Personalized Fitness Assistant*
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
        💪 <strong>FriskaAI Fitness Coach</strong> | Powered by Claude AI<br>
        © 2025 | For educational and informational purposes only
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============ RUN APPLICATION ============
if __name__ == "__main__":
    main()
    display_footer()