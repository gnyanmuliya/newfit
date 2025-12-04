import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import re
import random

# ============ CONFIGURATION & DATA DEFINITIONS ============

FITNESS_LEVELS = {
    'Level 1 – Assisted / Low Function': {'description': 'Requires significant support; focuses on basic movement and stability.', 'rpe_range': '2-3', 'max_complexity': 1},
    'Level 2 – Beginner Functional': {'description': 'Basic movement patterns, low impact, focus on form and core control.', 'rpe_range': '3-4', 'max_complexity': 2},
    'Level 3 – Moderate / Independent': {'description': 'Can perform unassisted movements with mild fatigue. Regular activity 2-3x/week.', 'rpe_range': '4-6', 'max_complexity': 3},
    'Level 4 – Active Wellness': {'description': 'Regular training experience, higher intensity, pushing strength and endurance limits.', 'rpe_range': '6-8', 'max_complexity': 4},
    'Level 5 – Adaptive Advanced': {'description': 'Highly experienced, requires advanced variations and maximal intensity/endurance work.', 'rpe_range': '7-9', 'max_complexity': 5},
}

GOAL_OPTIONS = [
    "Weight Loss", "Muscle Gain (Hypertrophy)", "Strength Gain", "Cardiovascular Fitness",
    "Flexibility & Mobility", "Rehabilitation & Injury Prevention", "Posture & Balance Improvement",
    "General Fitness", "Other (Custom Goal)"
]

MEDICAL_CONDITIONS = ["None", "Hypertension", "Obesity / Overweight", "Type 2 Diabetes", "Chronic Low Back Pain", "Osteoporosis", "Other"]

LOCATION_OPTIONS = ["Home", "Gym", "Outdoor"]

EQUIPMENT_OPTIONS = ["Bodyweight Only", "Dumbbells", "Resistance Bands", "Kettlebells",
                     "Barbell", "Bench", "Pull-up Bar", "Yoga Mat", "Machines", "Stable Chair", "TRX", "Cables"]

# ACSM time breakdown logic (minutes/exercise count) based on duration
DURATION_MAP = {
    # ADJUSTED MAIN COUNT FOR BETTER TRAINING DENSITY
    "15-20 minutes": {'total_time': 18, 'warmup_count': 3, 'cooldown_count': 3, 'main_count': 5}, 
    "20-30 minutes": {'total_time': 25, 'warmup_count': 3, 'cooldown_count': 3, 'main_count': 7},
    "30-45 minutes": {'total_time': 38, 'warmup_count': 3, 'cooldown_count': 3, 'main_count': 9},
    "45-60 minutes": {'total_time': 53, 'warmup_count': 3, 'cooldown_count': 3, 'main_count': 11},
}

EXERCISE_DATA_FILE = "Latest exercise database- New model.csv"

@st.cache_data
def load_exercise_data():
    """
    Loads the actual exercise database from CSV, cleans it, and creates required filtering columns.
    """
    try:
        # Load the actual CSV data
        df = pd.read_csv(EXERCISE_DATA_FILE, encoding='utf-8')
    except FileNotFoundError:
        st.error(f"❌ Error: Exercise database file '{EXERCISE_DATA_FILE}' not found. Please ensure the file is uploaded and in the correct directory.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error loading exercise data: {e}")
        return pd.DataFrame()

    # --- Data Cleaning and Augmentation ---
    
    # 1. Create numeric Complexity_Level from 'Fitness Level' string
    def extract_level_number(level_str):
        match = re.search(r'Level (\d+)', str(level_str))
        return int(match.group(1)) if match else 0
        
    df['Complexity_Level'] = df['Fitness Level'].apply(extract_level_number)
    
    # 2. Create list columns for filtering
    required_cols = ['Goals', 'Available Equipment', 'Category', 'Exercise Name', 'Target Region']
    if not all(col in df.columns for col in required_cols):
        st.error(f"Internal Error: Missing required columns in CSV: {list(set(required_cols) - set(df.columns))}")
        return pd.DataFrame()

    df['Goals_List'] = df['Goals'].apply(
        lambda x: [s.strip().lower() for s in str(x).split(',')] if pd.notna(x) else []
    )
    df['Equipment_List'] = df['Available Equipment'].apply(
        lambda x: [s.strip().lower() for s in str(x).replace("/", ",").split(',')] if pd.notna(x) else []
    )
    
    # 3. Create Concept Group (for variety/repetition checking)
    df['Concept_Group'] = df['Exercise Name'].str.split(' ').str[0].str.lower()
    
    # Ensure Category is clean for grouping
    df['Category'] = df['Category'].astype(str).str.strip()
    
    return df

# ============ CORE LOGIC FUNCTIONS ============

def calculate_bmi(weight_kg: float, height_cm: float) -> Optional[float]:
    """Calculates BMI from weight (kg) and height (cm)."""
    if weight_kg > 0 and height_cm > 0:
        return weight_kg / ((height_cm / 100) ** 2)
    return None

def get_session_counts(session_duration: str) -> Dict[str, int]:
    """Retrieves the target number of exercises for the session."""
    return DURATION_MAP.get(session_duration, DURATION_MAP["45-60 minutes"]) 

def get_training_split(days_count: int, fitness_level: str) -> List[str]:
    """
    Determines the workout distribution rule based on instructions.
    Rule 7: Levels 1-3 can repeat; Levels 4-5 use different/split exercises.
    """
    match = re.search(r'\d+', fitness_level)
    level_num = int(match.group(0)) if match else 3
    
    if days_count == 1:
        return ["Full-Body"]
    elif days_count == 2:
        return ["Full-Body A", "Full-Body B"] if level_num >= 4 else ["Full-Body A", "Full-Body A"]
    elif days_count == 3:
        # Levels 3-5: two same + one different (A-B-A pattern used for full-body split)
        return ["Full-Body A", "Full-Body B", "Full-Body A"] if level_num >= 3 else ["Full-Body A"] * 3
    elif days_count == 4:
        return ["Split A", "Split B", "Split A", "Split B"]
    elif days_count == 5:
        return ["Split A", "Split B", "Split A", "Split B", "Split A"]
    elif days_count == 6:
        return ["Split A", "Split B", "Split A", "Split B", "Split A", "Split B"]
    elif days_count == 7:
        return ["Split A", "Split B", "Active Recovery", "Split A", "Split B", "Split A", "Split B"]
    return ["Full-Body"] * days_count 

def filter_and_select_exercises(df: pd.DataFrame, profile: Dict[str, Any]) -> pd.DataFrame:
    """
    Filters the exercise dataframe based on ALL user profile and goal/level logic.
    Implements Location, Equipment, Safety, and Level-Based Exclusion.
    """
    
    filtered_df = df.copy()
    
    # Get required main exercise count for the fallback logic
    session_counts = get_session_counts(profile['session_duration'])
    target_main_count = session_counts['main_count']

    
    # 1. Safety Filter (Medical Conditions & Physical Limitations)
    medical_conditions = [c.lower() for c in profile.get('medical_conditions', []) if c != "None"]
    physical_limitations = profile.get('physical_limitations', '').lower()
    
    if (medical_conditions or physical_limitations) and 'Contraindications' in filtered_df.columns:
        exclusion_keywords = medical_conditions
        exclusion_keywords.extend([word.strip() for word in re.split(r'[^\w\s]', physical_limitations) if len(word) > 2])
        
        if exclusion_keywords:
            exclusion_pattern = '|'.join(re.escape(k) for k in exclusion_keywords)
            filtered_df = filtered_df[
                ~filtered_df['Contraindications'].fillna('').str.lower().str.contains(exclusion_pattern, na=False)
            ]
            st.info(f"Filtered out exercises contraindicated by: **{', '.join(exclusion_keywords[:3])}...**")
    
    # 2. Level & Complexity Filter 
    user_level_str = profile['fitness_level']
    user_max_complexity = FITNESS_LEVELS[user_level_str]['max_complexity']
    filtered_df = filtered_df[filtered_df['Complexity_Level'] <= user_max_complexity]
    
    # 2b. FIX: Exclude overly assisted movements for Level 3 and above (Lower/Upper Body)
    if user_max_complexity >= 3:
        # Targeting only highly modified or seated versions of strength work
        assisted_keywords = r'assisted|seated|wall' 
        is_strength_category = filtered_df['Category'].str.contains('Body|Strength', case=False, na=False)
        is_assisted = filtered_df['Exercise Name'].str.lower().str.contains(assisted_keywords, na=False)
        
        # Exclude strength exercises that are explicitly assisted for L3+
        filtered_df = filtered_df[~(is_strength_category & is_assisted)].copy()
        
    
    # 3. Equipment Filter (Rule 6)
    available_equipment = [e.lower().replace(" ", "") for e in profile.get('available_equipment', ["Bodyweight Only"])]
    
    def has_required_equipment(exercise_eq_list):
        # Check for bodyweight
        if 'bodyweightonly' in available_equipment and any('bodyweight' in eq for eq in exercise_eq_list):
            return True
        # Check for other required equipment
        for required_eq in exercise_eq_list:
            if required_eq.replace(" ", "") in available_equipment:
                return True
        return False
    
    filtered_df = filtered_df[filtered_df['Equipment_List'].apply(has_required_equipment)]


    # 4. Location Filter (Rule 5)
    location = profile.get('workout_location')
    
    if location == "Home":
        # Rule: Limit to bodyweight, dumbbells, resistance bands, or TRX.
        gym_only_forbidden = ['machines', 'barbells', 'cables', 'pull-upbar', 'barbell', 'cable'] 
        
        def is_home_compatible(exercise_eq_list):
            return not any(eq.replace(" ", "") in gym_only_forbidden for eq in exercise_eq_list)
        
        filtered_df = filtered_df[filtered_df['Equipment_List'].apply(is_home_compatible)]

    elif location == "Gym":
        # Rule: Include machines, barbells, and cables. Exclude outdoor-only.
        filtered_df = filtered_df[
            ~filtered_df['Available Equipment'].fillna('').str.lower().str.contains('outdoor only', na=False)
        ]
        
    elif location == "Outdoor":
        # Rule: Include walk, jog, step-ups, mobility drills, or bodyweight exercises.
        outdoor_allowed_eq = ['bodyweight', 'outdooronly', 'mat', 'wall', 'bench']
        
        def is_outdoor_compatible(exercise_eq_list):
             # An exercise is outdoor compatible if ALL its required equipment is in the allowed list
            return all(eq.replace(" ", "").replace("/", "").strip() in outdoor_allowed_eq for eq in exercise_eq_list)
        
        filtered_df = filtered_df[filtered_df['Equipment_List'].apply(is_outdoor_compatible)]
    
    
    # 5. Goal Alignment Filter (Conditional Relaxation for generation volume)
    goal_lower = profile['primary_goal'].lower().split('(')[0].strip()
    
    # Filter 1: Strict Goal Match
    strict_goal_df = filtered_df[filtered_df['Goals_List'].apply(
        lambda x: any(goal_lower in g for g in x)
    )].copy()
    
    # If strict goal matching is insufficient, relax the goal criteria.
    if len(strict_goal_df) < target_main_count:
        
        # Define secondary goals that are compatible with the primary goal 
        compatible_goals = [goal_lower, 'strength gain', 'general fitness', 'posture & balance improvement', 'cardiovascular fitness']
        
        relaxed_goal_df = filtered_df[filtered_df['Goals_List'].apply(
            lambda x: any(comp_goal in g for g in x for comp_goal in compatible_goals)
        )].copy()
        
        # Use the relaxed list only if it provides enough exercises.
        if len(relaxed_goal_df) >= target_main_count:
            filtered_df = relaxed_goal_df
        else:
            # If even the relaxed goal filter fails, use the widest possible filter that still respects safety/level/equipment.
            filtered_df = strict_goal_df if not strict_goal_df.empty else filtered_df

    else:
        filtered_df = strict_goal_df
        
    return filtered_df

# Global set to track the "concept" of used exercises across the week (e.g., 'squat', 'push-up')
used_concept_groups = set()

def generate_workout_plan(df_master: pd.DataFrame, profile: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Generates the full weekly plan with day-wise exercises and structure."""
    
    global used_concept_groups
    used_concept_groups = set() # Reset for a new plan generation
    
    filtered_df = filter_and_select_exercises(df_master, profile)
    
    if filtered_df.empty:
        return {"Error": pd.DataFrame()}

    # --- Grouping ---
    filtered_df['Category'] = filtered_df['Category'].astype(str)
    df_working = filtered_df.reset_index(drop=True)
    category_groups = {cat: group.copy() for cat, group in df_working.groupby('Category')}
    # ----------------

    session_counts = get_session_counts(profile['session_duration'])
    target_main_count = session_counts['main_count'] # 5, 7, 9, or 11
    target_warmup_count = session_counts['warmup_count'] # 3
    target_cooldown_count = session_counts['cooldown_count'] # 3
    
    main_categories = ["Upper Body", "Lower Body", "Core"] # Main three categories for balancing
    training_days = profile['days_per_week']
    split_rules = get_training_split(len(training_days), profile['fitness_level'])
    
    workout_plan = {}
    
    for day_index, (day, rule) in enumerate(zip(training_days, split_rules)):
        
        match = re.search(r'\d+', profile['fitness_level'])
        level_num = int(match.group(0)) if match else 3
        can_repeat_daily = level_num <= 3
        
        # 1. Warm-up (Always 3 if possible)
        warmup_pool = category_groups.get("Warm-Up", df_working[df_working['Category'].str.contains('Warm-Up|Cardio|Mobility', na=False)]).copy()
        warmup_selection = warmup_pool.sample(min(target_warmup_count, len(warmup_pool)), replace=False, random_state=42 + day_index)
        warmup_selection = warmup_selection.assign(Part='Warm-Up', Order=range(1, len(warmup_selection) + 1))
        
        # Add default Sets/RPE for W/CD if missing, required for strict output format
        warmup_selection['Sets'] = warmup_selection['Sets'].fillna(1)
        warmup_selection['RPE'] = warmup_selection['RPE'].fillna('2-4')


        # 2. Main Workout (Balanced Selection)
        if rule == "Active Recovery":
            main_selection = pd.DataFrame()
        else:
            main_pool = df_working[df_working['Category'].isin(main_categories) | 
                                   df_working['Category'].str.contains('Strength|Functional', case=False, na=False)].copy()
            
            main_selection_list = []
            
            # --- Proportional Target Calculation ---
            target_per_cat = target_main_count // len(main_categories)
            remainder = target_main_count % len(main_categories)
            
            # --- Check Available Concepts & Prioritize ---
            available_pool = main_pool[~main_pool['Concept_Group'].isin(used_concept_groups)].copy()
            
            if available_pool.empty:
                available_pool = main_pool.copy()
            
            categories_to_select = main_categories.copy()
            random.shuffle(categories_to_select)
            
            temp_selected_names = set()

            # FIX: Ensure we have at least 1 U, 1 L, 1 C if the target count allows it (>3 exercises)
            
            selection_targets = {cat: target_per_cat + (1 if i < remainder else 0) for i, cat in enumerate(main_categories)}
            
            # 2a. Guaranteed minimum selection for balanced Full Body (if target > 3)
            if target_main_count >= 3:
                for cat in main_categories:
                    cat_pool = available_pool[available_pool['Category'].str.contains(cat, case=False, na=False)].copy()
                    
                    if not cat_pool.empty:
                        # Select at least 1 exercise from each U/L/C category
                        selected_ex = cat_pool.sample(1, random_state=day_index + main_categories.index(cat) + 500)
                        main_selection_list.append(selected_ex)
                        
                        # Remove selected exercise's concept from future selection pool
                        available_pool = available_pool[~available_pool['Concept_Group'].isin(selected_ex['Concept_Group'].tolist())]
                        selection_targets[cat] -= 1
                        temp_selected_names.update(selected_ex['Exercise Name'].tolist())

            # 2b. Fill remaining slots based on the adjusted targets
            remaining_pool = available_pool.copy() # Pool of exercises whose concepts haven't been used yet
            
            for cat in main_categories:
                cat_count = selection_targets[cat]
                
                if cat_count > 0:
                    cat_pool = remaining_pool[remaining_pool['Category'].str.contains(cat, case=False, na=False)].copy()
                    
                    # Ensure we don't pick exercises already picked in the guaranteed step
                    cat_pool = cat_pool[~cat_pool['Exercise Name'].isin(temp_selected_names)]
                    
                    if not cat_pool.empty:
                        selected_ex = cat_pool.sample(min(cat_count, len(cat_pool)), replace=False, random_state=day_index + 600 + main_categories.index(cat))
                        main_selection_list.append(selected_ex)
                        temp_selected_names.update(selected_ex['Exercise Name'].tolist())


            # 2c. Final Consolidation and Reuse Logic
            if main_selection_list:
                main_selection = pd.concat([ex for ex in main_selection_list if not ex.empty]).drop_duplicates(subset=['Exercise Name'])
                
                # If we still haven't met the target count, fill by reusing/shuffling the full pool.
                while len(main_selection) < target_main_count:
                    fill_needed = target_main_count - len(main_selection)
                    reusable_pool = main_pool[~main_pool['Exercise Name'].isin(main_selection['Exercise Name'])]
                    
                    if reusable_pool.empty: break
                        
                    reused_selection = reusable_pool.sample(min(fill_needed, len(reusable_pool)), replace=False, random_state=day_index + len(main_selection) + 700)
                    main_selection = pd.concat([main_selection, reused_selection]).drop_duplicates(subset=['Exercise Name'])

                # Update the concept group tracker
                used_concept_groups.update(main_selection['Concept_Group'].tolist())
                
                # Final shuffle and assignment
                main_selection = main_selection.sample(frac=1, random_state=day_index) 
                main_selection = main_selection.head(target_main_count).assign(Part='Main Workout', Order=range(1, len(main_selection) + 1))
            else:
                main_selection = pd.DataFrame()
                
        # 3. Cool-Down (Always 3 if possible)
        cooldown_pool = category_groups.get("Cool-Down", df_working[df_working['Category'].str.contains('Cool-Down|Stretch|Mobility', na=False)]).copy()
        cooldown_selection = cooldown_pool.sample(min(target_cooldown_count, len(cooldown_pool)), replace=False, random_state=42 + day_index * 2)
        cooldown_selection = cooldown_selection.assign(Part='Cool-Down', Order=range(1, len(cooldown_selection) + 1))
        
        # Add default Sets/RPE for W/CD if missing, required for strict output format
        cooldown_selection['Sets'] = cooldown_selection['Sets'].fillna(1)
        cooldown_selection['RPE'] = cooldown_selection['RPE'].fillna('2-4')
        
        # Combine
        daily_plan = pd.concat([warmup_selection, main_selection, cooldown_selection]).reset_index(drop=True)
        
        # Demographic Adjustments (ACSM guideline implementation)
        if profile['age'] >= 60 or (profile['bmi'] is not None and profile['bmi'] >= 30):
            daily_plan['RPE'] = daily_plan['RPE'].apply(lambda x: re.sub(r'(\d+)-(\d+)', lambda m: f"{max(1, int(m.group(1))-1)}-{max(2, int(m.group(2))-1)}", x))
            daily_plan['Safety Cue'] += " (Prioritize stability and balance.)"
        
        if profile['gender'] == 'Female':
            daily_plan['RPE'] = daily_plan['RPE'].apply(lambda x: re.sub(r'(\d+)-(\d+)', lambda m: f"{m.group(1)}-{max(2, int(m.group(2))-1)}", x))

        workout_plan[day] = daily_plan
        
    return workout_plan

# ============ DISPLAY FUNCTIONS (Strict Custom Format) ============

def display_exercise_plan(workout_plan: Dict[str, pd.DataFrame], profile: Dict[str, Any]):
    """Displays the final exercise plan in the requested detailed custom format for ALL exercises."""
    
    if "Error" in workout_plan:
        st.error("❌ No exercises matched your profile criteria. Try adjusting your selections (especially equipment or fitness level).")
        return

    st.markdown("---")
    st.header(f"👋 Welcome, {profile.get('name', 'User')}!")
    st.subheader("Your Personalized Fitness Plan is Ready")
    
    # Header Info
    st.markdown(f"""
        📅 Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        🎯 Goal: **{profile['primary_goal']}** | 
        💪 Level: **{profile['fitness_level']}**
    """)
    
    st.markdown("\n\n")
    st.subheader("📅 Your Weekly Workout Schedule")

    for day, df_plan in workout_plan.items():
        st.markdown(f"## 📋 {day} Workout")
        
        main_df = df_plan[df_plan['Part'] == 'Main Workout']
        focus = "Full Body"
        if not main_df.empty:
            focus_counts = main_df['Category'].value_counts()
            if not focus_counts.empty:
                primary_focus = focus_counts.index[0]
                focus = f"{focus} ({primary_focus} Focus)"

        st.markdown(f"**{day} – {focus}**")
        
        exercise_count = 0
        
        for part, group in df_plan.groupby('Part', sort=False):
            
            time_estimate = " (5-7 minutes)" if part in ['Warm-Up', 'Cool-Down'] else ""
            st.markdown(f"### {part}{time_estimate}")
            
            
            for idx, row in group.iterrows():
                exercise_count += 1
                
                # Retrieve details, filling defaults for W/CD
                sets = row.get('Sets', 1)
                reps = row.get('Reps', 'N/A')
                rpe = row.get('RPE', 'N/A')
                rest = row.get('Rest Intervals', 'N/A')
                
                # Title
                st.markdown(f"**{exercise_count}. {row['Exercise Name']}**")
                
                # Benefit
                st.markdown(f"**Benefit**: {row.get('Health Benefit', 'N/A')}")
                
                # How to Perform (numbered list format)
                st.markdown("**How to Perform:**")
                
                # Split raw instruction string by ". " to separate sentences/steps
                raw_instructions = row.get('Steps to Perform', 'N/A').strip()
                # Use regex to split by period followed by optional space, ensuring we capture sentences cleanly
                steps = [s.strip() for s in re.split(r'\.\s*', raw_instructions) if s.strip()]
                
                # Build the instruction block with fixed indentation
                step_markdown = ""
                step_number = 1
                for step_content in steps:
                    
                    # Ensure the step number is clean (remove any initial numbers/dots from CSV)
                    step_content = re.sub(r'^\d+\.?\s*', '', step_content).strip()
                    
                    if step_content:
                        # Add a trailing period if one is missing (since we split by it)
                        if not step_content.endswith('.'):
                            step_content += '.'
                            
                        # FIX: Using HTML line break (<br>) and non-breaking spaces for indent. 
                        # This should eliminate the messy intermediate numbering/spacing issue.
                        step_markdown += f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{step_number}. {step_content}<br>"
                        step_number += 1
                
                st.markdown(step_markdown, unsafe_allow_html=True)
                        
                # Details (no columns used, strictly sequential markdown lines)
                st.markdown(f"**Sets**: {sets}")
                st.markdown(f"**Reps**: {reps}")
                st.markdown(f"**Intensity**: RPE {rpe}")
                st.markdown(f"**Rest**: {rest}")
                st.markdown(f"**Equipment**: {row.get('Available Equipment', 'N/A')}")
                st.markdown(f"**Safety Cue**: {row.get('Safety Cue', 'N/A')}")
                
                st.markdown("\n") # Add extra line after each exercise
            
            st.markdown("---")

# ============ MAIN APP ============
def main():
    """Main application function."""
    
    st.set_page_config(page_title="FriskaAI Fitness Coach", page_icon="💪", layout="wide")
    st.title("💪 FriskaAI Fitness Coach")
    st.markdown("Get a personalized, ACSM-aligned workout plan based on your comprehensive profile.")
    
    df_exercise = load_exercise_data()
    if df_exercise.empty:
        pass
    
    # Initialize session state with all required fields
    if 'profile_state' not in st.session_state:
        st.session_state.profile_state = {
            'name': 'Gnyan', 'age': 30, 'gender': 'Male', 
            'unit_system': 'Metric (kg, cm)', 'weight_kg': 70.0, 'height_cm': 170.0, 'bmi': 24.2,
            'primary_goal': 'Muscle Gain (Hypertrophy)', 'secondary_goal': 'None',
            'fitness_level': 'Level 3 – Moderate / Independent', 
            'medical_conditions': ["None"],
            'physical_limitations': '',
            'days_per_week': ["Monday", "Wednesday", "Friday"], 
            'session_duration': '30-45 minutes',
            'available_equipment': ["Bodyweight Only", "Dumbbells", "Stable Chair", "Yoga Mat"], 
            'workout_location': 'Home',
        }
    
    profile = st.session_state.profile_state
    
    # ============ THE FORM ============
    with st.form("fitness_form"):
        
        # 1. Basic Info
        st.subheader("📋 Basic Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            name = st.text_input("Name *", value=profile.get('name', ''), placeholder="Enter your name")
            age = st.number_input("Age *", min_value=13, max_value=100, value=profile.get('age', 30))
        
        with col2:
            gender = st.selectbox("Gender *", ["Male", "Female", "Other"], 
                                 index=["Male", "Female", "Other"].index(profile.get('gender', 'Male')))
            workout_location = st.selectbox("Workout Location *", LOCATION_OPTIONS,
                                            index=LOCATION_OPTIONS.index(profile.get('workout_location', 'Home')))

        with col3:
            unit_system = st.radio("Units *", ["Metric (kg, cm)", "Imperial (lbs, in)"], 
                                  index=["Metric (kg, cm)", "Imperial (lbs, in)"].index(profile.get('unit_system', 'Metric (kg, cm)')))
            
        col_w, col_h, col_bmi = st.columns(3)
        with col_w:
            weight_kg = 0.0
            if unit_system == "Metric (kg, cm)":
                weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=profile.get('weight_kg', 70.0))
            else:
                weight_lbs = st.number_input("Weight (lbs) *", min_value=66.0, max_value=660.0, value=profile.get('weight_kg', 70.0) / 0.453592)
                weight_kg = weight_lbs * 0.453592
        
        with col_h:
            height_cm = 0.0
            if unit_system == "Metric (kg, cm)":
                height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=profile.get('height_cm', 170.0))
            else:
                height_in = st.number_input("Height (in) *", min_value=39.0, max_value=98.0, value=profile.get('height_cm', 170.0) / 2.54)
                height_cm = height_in * 2.54
                
        with col_bmi:
            current_bmi = calculate_bmi(weight_kg, height_cm)
            bmi_display = f"{current_bmi:.1f}" if current_bmi else "N/A"
            bmi_type = ""
            if current_bmi:
                if current_bmi < 18.5: bmi_type = " (Underweight)"
                elif current_bmi < 25: bmi_type = " (Normal)"
                elif current_bmi < 30: bmi_type = " (Overweight)"
                else: bmi_type = " (Obese)"
            st.info(f"📊 Your BMI: {bmi_display}{bmi_type}")

        # 2. Fitness Goals & Level
        st.subheader("🎯 Fitness Goals & Level")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            primary_goal = st.selectbox("Primary Goal *", GOAL_OPTIONS, 
                                       index=GOAL_OPTIONS.index(profile.get('primary_goal', 'Muscle Gain (Hypertrophy)')))
        
        with col_g2:
            secondary_options = ["None"] + [g for g in GOAL_OPTIONS if g != primary_goal]
            secondary_goal = st.selectbox("Secondary Goal (Optional)", secondary_options, 
                                         index=secondary_options.index(profile.get('secondary_goal', 'None')))
        
        fitness_level = st.selectbox("Fitness Level *", list(FITNESS_LEVELS.keys()), 
                                    index=list(FITNESS_LEVELS.keys()).index(profile.get('fitness_level', 'Level 3 – Moderate / Independent')))
        
        level_info = FITNESS_LEVELS[fitness_level]
        st.info(f"**{fitness_level}**: {level_info['description']} | **RPE**: {level_info['rpe_range']}")
        
        # 3. Health Screening
        st.subheader("🏥 Health Screening")
        medical_conditions = st.multiselect("Medical Conditions * (Used for exercise exclusion)", MEDICAL_CONDITIONS, 
                                           default=profile.get('medical_conditions', ["None"]))
        
        st.warning("⚠️ **Physical Limitations** - Describe ANY injuries, pain, or movement restrictions")
        physical_limitations = st.text_area("Physical Limitations (Important for Safety) *", 
                                           value=profile.get('physical_limitations', ''),
                                           placeholder="E.g., 'Previous right knee surgery - avoid deep squats'",
                                           height=100)
        
        # 4. Training Schedule & Equipment
        st.subheader("💪 Training Schedule & Equipment")
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            days_per_week = st.multiselect("Preferred Training Days *", 
                                          ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                          default=profile.get('days_per_week', ["Monday", "Wednesday", "Friday"]))
            session_duration = st.selectbox("Preferred Session Duration *", 
                                           list(DURATION_MAP.keys()),
                                           index=list(DURATION_MAP.keys()).index(profile.get('session_duration', '30-45 minutes')))
        
        with col_t2:
            equipment = st.multiselect("Select all available equipment:", EQUIPMENT_OPTIONS, 
                                  default=profile.get('available_equipment', ["Bodyweight Only", "Dumbbells", "Stable Chair", "Yoga Mat"]))
            if not equipment: equipment = ["Bodyweight Only"]
            
        st.markdown("---")
        
        submit_clicked = st.form_submit_button("🚀 Generate My Exercise Plan (ACSM-Aligned)", 
                                              use_container_width=True, type="primary")
        
        if submit_clicked:
            if df_exercise.empty:
                st.error("Cannot generate plan: The exercise database failed to load. Please check the file path.")
            elif not name or len(name.strip()) < 2:
                st.error("❌ Please enter your name.")
            elif not days_per_week:
                st.error("❌ Please select at least one training day.")
            elif weight_kg <= 0 or height_cm <= 0:
                st.error("❌ Please ensure valid weight and height inputs.")
            else:
                profile_data = {
                    'name': name, 'age': age, 'gender': gender, 'unit_system': unit_system,
                    'weight_kg': weight_kg, 'height_cm': height_cm, 'bmi': current_bmi,
                    'primary_goal': primary_goal, 'secondary_goal': secondary_goal,
                    'fitness_level': fitness_level, 'medical_conditions': medical_conditions,
                    'physical_limitations': physical_limitations,
                    'days_per_week': days_per_week, 'session_duration': session_duration,
                    'available_equipment': equipment, 'workout_location': workout_location,
                }
                st.session_state.profile_state = profile_data
                
                st.markdown("## 🔍 Analyzing Profile and Generating Plan...")
                with st.spinner("Filtering, substituting, and structuring your plan based on ACSM guidelines..."):
                    workout_plan = generate_workout_plan(df_exercise, profile_data)
                    display_exercise_plan(workout_plan, profile_data)
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p><strong>⚠️ Medical Disclaimer:</strong> This plan is for informational purposes only and is not medical advice. 
        Consult a healthcare professional before beginning any new exercise regimen.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == '__main__':
    main()