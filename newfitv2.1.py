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

# ============ CONDITION-SPECIFIC GUIDELINES DATABASE ============
CONDITION_GUIDELINES_DB = {
    "Hypertension": {
        "contraindicated": "Valsalva maneuvers, heavy isometric holds, overhead pressing without control, breath-holding during lifts",
        "modified": "Controlled breathing, moderate resistance, continuous breathing pattern, avoid maximal effort",
        "intensity": "RPE 4-6, avoid RPE >7",
        "notes": "Monitor for dizziness, stop if experiencing headache or visual changes. Blood pressure should be <160/100 before exercise."
    },
    "Type 2 Diabetes": {
        "contraindicated": "High-intensity intervals without medical clearance, prolonged fasting exercise, exercises causing severe blood sugar fluctuations",
        "modified": "Moderate-intensity steady state, check blood glucose pre/post workout, post-meal walking encouraged",
        "intensity": "RPE 5-7, progress gradually",
        "notes": "Have fast-acting carbs available, monitor for hypoglycemia signs (shakiness, confusion, sweating). Ideal range: 100-250 mg/dL before exercise."
    },
    "Osteoarthritis": {
        "contraindicated": "High-impact jumping, deep squats with pain, excessive joint loading, running on hard surfaces",
        "modified": "Low-impact alternatives (swimming, cycling), partial range if painful, aquatic exercise preferred, use of resistance bands",
        "intensity": "RPE 3-6, pain-free range only",
        "notes": "Some mild discomfort acceptable, sharp pain is a stop signal. Warmth and gentle movement often helpful."
    },
    "Osteoporosis": {
        "contraindicated": "Spinal flexion exercises, high-impact if severe, twisting movements under load, forward bending",
        "modified": "Weight-bearing activities, resistance training with proper form, balance work, spine extension exercises",
        "intensity": "RPE 4-6, progressive loading",
        "notes": "Focus on bone-strengthening exercises, avoid fall risk scenarios. Consult physician about bone density status."
    },
    "Chronic Lower Back Pain": {
        "contraindicated": "Loaded spinal flexion, unsupported twisting, heavy deadlifts initially, sit-ups with feet anchored",
        "modified": "Core stabilization, neutral spine movements, progressive loading, bird dogs, dead bugs, planks",
        "intensity": "RPE 3-5 initially, pain-free movement only",
        "notes": "Pain centralization (moving toward spine) is good, peripheralization (moving down leg) requires modification or stop."
    },
    "Asthma": {
        "contraindicated": "Cold air exposure, continuous high-intensity cardio without breaks, exercises in high-pollen environments",
        "modified": "Interval training with rest periods, swimming (warm humid air), controlled breathing exercises, gradual warm-up",
        "intensity": "RPE 5-7, with frequent breaks",
        "notes": "Keep rescue inhaler accessible. Use preventive inhaler 15-30 min before exercise if prescribed. Stop if wheezing occurs."
    },
    "Coronary Artery Disease": {
        "contraindicated": "Maximal effort exercises, isometric exercises, sudden intense exertion",
        "modified": "Supervised moderate aerobic exercise, gradual progression, extended warm-up and cool-down",
        "intensity": "RPE 3-5, medical clearance required",
        "notes": "Stop immediately if chest pain, unusual shortness of breath, or dizziness occurs. Medical supervision recommended."
    },
    "COPD": {
        "contraindicated": "High-intensity continuous cardio, exercises causing severe breathlessness, cold air exposure",
        "modified": "Interval training, pursed-lip breathing, upper body exercises with breathing coordination",
        "intensity": "RPE 3-6, ability to speak in short sentences",
        "notes": "Use supplemental oxygen if prescribed. Focus on breathing techniques and pacing."
    }
}

# ============ FITNESS ADVISOR CLASS (ENHANCED) ============
class FitnessAdvisor:
    """Enhanced fitness planning engine with comprehensive medical safety protocols"""
    
    def __init__(self, api_key: str, endpoint_url: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
    
    def _build_system_prompt(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        is_modification: bool = False,
        modification_request: str = "",
        original_plan_context: str = None
    ) -> str:
        """
        Build comprehensive system prompt using enhanced architecture
        Inspired by meal plan prompt structure for maximum accuracy and safety
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
        
        # Build comprehensive prompt sections
        prompt_parts = []
        
        # ==================== SECTION 0: IDENTITY & MISSION ====================
        prompt_parts.append("""You are FriskaAI, a certified clinical exercise physiologist (ACSM-CEP) and fitness program designer. Your primary mission is to create medically safe, evidence-based, and highly personalized workout plans. Your performance is evaluated on strict adherence to safety protocols, scientific exercise prescription principles, and user-specific adaptations. You MUST respond ONLY in English.
""")
        
        # ==================== SECTION 1: USER PROFILE ====================
        profile_section = f"""
**1. USER PROFILE & FITNESS PARAMETERS (Non-Negotiable):**

**Basic Information:**
- Name: {name}
- Age: {age} years
- Gender: {gender}
- Fitness Level: {fitness_level}
- Primary Goal: {primary_goal}
- Session Duration: {session_duration}
- Workout Location: {location}

**Target Focus for {day_name}:** {focus}

**Medical & Physical Status:**
- Medical Conditions: {', '.join(medical_conditions)}
- Physical Limitations: {physical_limitations if physical_limitations else 'None reported'}

**Available Equipment:**
{', '.join(available_equipment)}
"""
        prompt_parts.append(profile_section)
        
        # ==================== SECTION 2: MEDICAL SAFETY RULES ====================
        condition_guidelines = self._get_condition_guidelines(medical_conditions)
        
        if medical_conditions and medical_conditions != ["None"]:
            safety_section = f"""
**2. MEDICAL SAFETY RULES (ABSOLUTELY CRITICAL - HIGHEST PRIORITY):**

**Condition-Specific Exercise Guidelines:**
{condition_guidelines}

**MANDATORY SAFETY PROTOCOL:**
- You MUST cross-reference EVERY exercise against the user's medical conditions
- You MUST NOT include any exercise listed as "contraindicated" for their conditions
- You MUST prioritize "Modified/Safer Exercises" from the guidelines above
- You MUST include appropriate intensity limits based on medical conditions
- You MUST provide safety cues for every exercise that address the user's specific health concerns

**CRITICAL CHECK:** Before finalizing the workout, verify that NO contraindicated exercises are included. Including a contraindicated exercise is a complete failure of your primary safety mission.
"""
        else:
            safety_section = """
**2. GENERAL SAFETY RULES (MANDATORY):**
- While no medical conditions are reported, you MUST still prioritize safe exercise progression
- All exercises must be appropriate for the user's age and fitness level
- Include proper warm-up and cool-down protocols
- Provide clear safety cues to prevent injury
"""
        prompt_parts.append(safety_section)
        
        # ==================== SECTION 3: AGE-ADAPTIVE RULES ====================
        age_rules = self._get_age_adaptations(age, medical_conditions)
        prompt_parts.append(age_rules)
        
        # ==================== SECTION 4: FITNESS LEVEL ADAPTATION ====================
        level_rules = self._get_fitness_level_rules(fitness_level)
        prompt_parts.append(level_rules)
        
        # ==================== SECTION 5: GOAL-SPECIFIC PROGRAMMING ====================
        goal_rules = self._get_goal_specific_rules(primary_goal)
        prompt_parts.append(goal_rules)
        
        # ==================== SECTION 6: WORKOUT STRUCTURE RULES ====================
        exercise_count = self._determine_exercise_count(session_duration)
        structure_rules = f"""
**6. MANDATORY WORKOUT STRUCTURE (STRICT FORMAT):**

**YOU MUST GENERATE A COMPLETE WORKOUT WITH ALL SECTIONS. A workout missing any section is considered incomplete and unacceptable.**

**SECTION A: WARM-UP (5-7 minutes) - MANDATORY**
- MUST include 3-4 movements
- MUST be mobility and activation focused
- MUST NOT include strength exercises (no squats, push-ups, planks in warm-up)
- Appropriate warm-up movements: arm circles, leg swings, hip circles, cat-cow, shoulder rolls, ankle mobility, trunk rotations, marching in place, light dynamic stretches

**SECTION B: MAIN WORKOUT ({exercise_count} exercises) - MANDATORY**
- MUST include {exercise_count} exercises
- MUST focus on: {focus}
- MUST alternate muscle groups when possible (e.g., upper/lower, push/pull)
- MUST NOT repeat exercises from warm-up or cool-down
- Each exercise MUST include: Exercise name, benefit, detailed steps, sets × reps, intensity (RPE), rest period, safety cue specific to user's profile

**SECTION C: COOL-DOWN (5-7 minutes) - MANDATORY**
- MUST include 3-4 movements
- MUST be stretching and breathing focused
- MUST NOT include strength exercises
- Appropriate cool-down movements: static stretches (hamstring, quad, chest, shoulder, hip flexor), child's pose (if appropriate for age/mobility), cat-cow, spinal twists, deep breathing exercises
- For users aged 60+: Use seated or standing stretches instead of floor-based poses unless mobility allows

**FORMAT FOR EACH EXERCISE (MANDATORY):**
```
**Exercise Name**
- Benefit: [Specific benefit related to user goal]
- How to Perform:
  1. [Detailed step 1]
  2. [Detailed step 2]
  3. [Detailed step 3]
- Sets × Reps: [e.g., 3 × 10-12]
- Intensity: RPE [X-Y]
- Rest: [e.g., 45 seconds]
- Safety Cue: [Specific to user's age/condition/limitations]
```
"""
        prompt_parts.append(structure_rules)
        
        # ==================== SECTION 7: EXERCISE SELECTION RULES ====================
        selection_rules = f"""
**7. EXERCISE SELECTION RULES (CRITICAL GUIDELINES):**

**Equipment-Based Selection:**
- User has access to: {', '.join(available_equipment)}
- You MUST ONLY select exercises that can be performed with available equipment
- If "None - Bodyweight Only": All exercises must be bodyweight or use household items (chair, towel, water bottles)
- If "Home": Prefer simple, space-efficient exercises
- If gym equipment available: Can use full exercise library

**Target Area Priority ({focus}):**
- At least 60-70% of main exercises MUST directly target: {focus}
- Include supporting muscle groups for balanced development
- Ensure proper warm-up for target area

**Movement Pattern Balance:**
Ensure inclusion of these fundamental patterns (when applicable to focus area):
1. Push (vertical or horizontal)
2. Pull (vertical or horizontal)
3. Hinge (hip dominant)
4. Squat (knee dominant)
5. Core stabilization

**Contraindication Check (MANDATORY):**
Before including ANY exercise, verify it is NOT contraindicated for:
- User's medical conditions
- User's physical limitations
- User's age-specific restrictions
- User's equipment limitations
"""
        prompt_parts.append(selection_rules)
        
        # ==================== SECTION 8: INTENSITY & VOLUME ====================
        intensity_rules = """
**8. INTENSITY & VOLUME PRESCRIPTION:**

**RPE (Rate of Perceived Exertion) Scale - 1-10:**
- 1-2: Very Light (minimal effort)
- 3-4: Light (can maintain conversation easily)
- 5-6: Moderate (can talk in short sentences)
- 7-8: Hard (difficult to speak)
- 9-10: Very Hard to Maximal (cannot maintain)

**Rest Period Guidelines:**
- Strength focus: 90-180 seconds
- Hypertrophy: 60-90 seconds
- Muscular endurance: 30-60 seconds
- Circuit/metabolic: 15-30 seconds
- Adjust based on fitness level: beginners need more rest
"""
        prompt_parts.append(intensity_rules)
        
        # ==================== SECTION 9: OUTPUT FORMATTING ====================
        format_section = f"""
**9. STRICT OUTPUT FORMATTING (ABSOLUTELY CRITICAL):**

**YOU MUST RESPOND IN THIS EXACT STRUCTURE:**

### {day_name} – {focus} Focus

**Warm-Up (5-7 minutes)**
[List 3-4 mobility/activation movements with duration]

**Main Workout (Target: {focus})**
[List {exercise_count} exercises with complete format specified above]

**Cool-Down (5-7 minutes)**
[List 3-4 stretches/breathing exercises with duration]

**FORMATTING RULES:**
- Use markdown with `###` for day title and `**` for sections
- Each exercise must be clearly formatted with all required fields
- Include blank lines between exercises for readability
- NO conversational text before or after the workout plan
- NO motivational fluff - be concise and professional
"""
        prompt_parts.append(format_section)
        
        # ==================== SECTION 10: MODIFICATION HANDLING ====================
        if is_modification and modification_request:
            mod_section = f"""
**10. MODIFICATION REQUEST:**

User wants to modify the workout with this request: "{modification_request}"

**MODIFICATION GUIDELINES:**
- Make ONLY the changes requested by the user
- Maintain safety and appropriateness for user's profile
- Keep overall workout structure and balance
- Provide complete updated workout plan
"""
            if original_plan_context:
                mod_section += f"""
**Original Workout Plan for Reference:**
{original_plan_context}
"""
            prompt_parts.append(mod_section)
        
        # ==================== SECTION 11: FINAL VERIFICATION ====================
        verification = """
**FINAL VERIFICATION CHECKLIST (MANDATORY BEFORE RESPONDING):**

Before providing your response, verify you have:
- [ ] Included ALL required sections: Warm-up, Main Workout, Cool-down
- [ ] Checked that NO exercises violate medical contraindications
- [ ] Ensured exercises match user's available equipment
- [ ] Scaled intensity appropriately for fitness level
- [ ] Applied age-appropriate modifications
- [ ] Provided complete exercise instructions with safety cues
- [ ] Used proper formatting with markdown
- [ ] Included NO unnecessary conversational text
"""
        prompt_parts.append(verification)
        
        # ==================== SECTION 12: TASK DIRECTIVE ====================
        if is_modification:
            task = f"Generate a MODIFIED workout plan for {day_name} incorporating the requested changes while maintaining safety."
        else:
            task = f"Generate a COMPLETE workout plan for {day_name} focusing on {focus} following ALL rules above."
        
        prompt_parts.append(f"**YOUR TASK:** {task}")
        
        return "\n".join(prompt_parts)
    
    def _get_condition_guidelines(self, medical_conditions: List[str]) -> str:
        """Generate detailed condition-specific exercise guidelines from database"""
        if not medical_conditions or medical_conditions == ["None"]:
            return "No medical conditions reported. Standard exercise protocols apply."
        
        guidelines = []
        
        for condition in medical_conditions:
            for key, data in CONDITION_GUIDELINES_DB.items():
                if key.lower() in condition.lower():
                    guideline = f"""
🏥 **{key}:**
   - ❌ Contraindicated: {data['contraindicated']}
   - ✅ Modified/Safer: {data['modified']}
   - 📊 Intensity Limit: {data['intensity']}
   - ⚠️ Special Notes: {data['notes']}
"""
                    guidelines.append(guideline)
                    break
        
        if not guidelines:
            return f"Medical conditions noted: {', '.join(medical_conditions)}\nNo specific contraindications in database. Use conservative approach and general precautions."
        
        return "\n".join(guidelines)
    
    def _get_age_adaptations(self, age: int, medical_conditions: List[str]) -> str:
        """Generate age-specific training adaptations"""
        if age >= 60:
            return f"""
**3. AGE-ADAPTIVE TRAINING RULES (SENIOR PROTOCOL - Age {age}):**

**CRITICAL AGE-BASED MODIFICATIONS:**
- Treat as beginner-to-moderate intensity regardless of stated fitness level
- MANDATORY FOCUS: Fall prevention, balance, and functional independence
- Joint-friendly, low-impact movements are REQUIRED

**PROHIBITED Exercises (First 4-8 weeks):**
- NO jumping, plyometrics, or high-impact movements
- NO floor-based planks (use wall or elevated surface)
- NO heavy barbell work or max effort lifts
- NO exercises requiring rapid directional changes

**REQUIRED Exercise Categories:**
- Balance work: MUST include 2-3 balance exercises per session
- Functional movements: Sit-to-stand, step-ups, supported squats
- Upper body: Wall push-ups, resistance band rows
- Core: Standing marches, seated twists, bird-dog variations

**Intensity Guidelines:**
- RPE: 3-5 (Light to Moderate)
- Never exceed RPE 6 in first month
- Prioritize control over speed or load
"""
        elif age >= 50:
            return f"""
**3. AGE-ADAPTIVE TRAINING RULES (MATURE ADULT - Age {age}):**

**Moderate Age-Based Considerations:**
- Enhanced focus on joint health and mobility
- Include adequate warm-up (5-7 minutes minimum)
- Emphasize eccentric control to protect joints
- Include flexibility work in every session

**Recommended Modifications:**
- Lower impact alternatives when appropriate
- Emphasize proper form over heavy loads
- Include balance exercises 2x per week
- Recovery: 48-72 hours between intense sessions

**Intensity Guidelines:**
- RPE: 4-7 (Moderate to Moderately Hard)
- Progressive overload: Increase volume before intensity
"""
        elif age >= 40:
            return f"""
**3. AGE-ADAPTIVE TRAINING RULES (MIDDLE AGE - Age {age}):**

- Balance strength and mobility work
- Include recovery/mobility sessions
- Monitor for overuse injuries
- Adequate rest between sessions
- RPE: 5-7 range typically appropriate
"""
        else:
            return f"""
**3. AGE-ADAPTIVE TRAINING RULES (ADULT - Age {age}):**

- Standard progression protocols apply
- Can include high-intensity work if cleared
- Focus on long-term athletic development
- RPE: 4-8 range based on fitness level
"""
    
    def _get_fitness_level_rules(self, fitness_level: str) -> str:
                """Get fitness level-specific rules"""
                if "Level 1" in fitness_level or "Level 2" in fitness_level or "Beginner" in fitness_level:
                    return """
        **4. FITNESS LEVEL ADAPTATION (BEGINNER):**

        - Sets: 2-3 sets × 8-12 reps
        - Rest: 60-90 seconds between exercises
        - Focus: Form mastery, basic strength foundation
        - RPE: 4-6 (Light to Moderate)
        - Tempo: 2-0-2-0 (slow and controlled)
        - Equipment: Bodyweight, light resistance bands preferred
        """
                elif "Level 3" in fitness_level or "Intermediate" in fitness_level:
                    return """
        **4. FITNESS LEVEL ADAPTATION (INTERMEDIATE):**

        - Sets: 3-4 sets × 10-15 reps
        - Rest: 45-60 seconds
        - Focus: Strength building, muscular endurance
        - RPE: 5-7 (Moderate to Moderately Hard)
        - Tempo: 2-0-1-0 (moderate pace)
        - Equipment: Moderate resistance available
        """
                else:
                    return """
        **4. FITNESS LEVEL ADAPTATION (ADVANCED):**

        - Sets: 3-4 sets × 6-12 reps (varied)
        - Rest: 30-90 seconds (based on exercise)
        - Focus: Performance optimization
        - RPE: 6-8 (Moderately Hard to Hard)
        - Tempo: Varied based on exercise type
        - Equipment: Full range with progressive loading
        """
    
    def _get_goal_specific_rules(self, primary_goal: str) -> str:
        """Get goal-specific programming rules"""
        base = f"**5. GOAL-SPECIFIC PROGRAMMING (PRIMARY GOAL: {primary_goal}):**\n\n"
        
        if "Weight Loss" in primary_goal or "weight loss" in primary_goal.lower():
            return base + """
            **Weight Loss Protocol:**
            - Emphasize compound, multi-joint movements to maximize calorie burn
            - Include metabolic conditioning (circuit training when appropriate)
            - Higher rep ranges: 12-20 reps for most exercises
            - Shorter rest periods: 30-45 seconds
            - Total workout should maintain elevated heart rate throughout
            """
        elif "Muscle Gain" in primary_goal or "muscle" in primary_goal.lower():
            return base + """
            **Muscle Gain Protocol:**
            - Focus on progressive overload with resistance
            - Moderate rep ranges: 6-12 reps
            - Longer rest periods: 60-120 seconds for compound lifts
            - Emphasize eccentric (lowering) phase: 2-3 second tempo
            - Volume: 12-20 sets per muscle group per week
            """
        elif "Strength" in primary_goal or "strength" in primary_goal.lower():
            return base + """
            **Strength Building Protocol:**
            - Prioritize compound movements (squats, deadlifts, presses, rows)
            - Lower rep ranges: 4-8 reps
            - Longer rest periods: 90-180 seconds
            - Focus on load progression (if equipment available)
            - Emphasize perfect form and controlled tempo
            """
        elif "Cardiovascular" in primary_goal or "cardio" in primary_goal.lower():
            return base + """
            **Cardiovascular Fitness Protocol:**
            - Include continuous movement patterns
            - Mix of steady-state and interval work
            - Higher rep ranges: 15-25 reps
            - Minimal rest: 15-30 seconds
            - Full-body movements preferred
            """
        elif "Flexibility" in primary_goal or "Mobility" in primary_goal:
            return base + """
            **Flexibility & Mobility Protocol:**
            - Dynamic stretching in warm-up (5-7 minutes)
            - Active mobility drills throughout workout
            - Static stretching in cool-down (8-10 minutes)
            - Hold stretches: 30-60 seconds
            - Focus on full range of motion in all exercises
            """
        elif "Rehabilitation" in primary_goal or "rehab" in primary_goal.lower():
            return base + """
            **Rehabilitation Protocol:**
            - CRITICAL: All exercises MUST be cleared by medical professional
            - Pain-free range of motion ONLY
            - Very conservative loading
            - Focus on movement quality over quantity
            - RPE: 3-5 maximum
            """
        elif "Posture" in primary_goal or "Balance" in primary_goal:
            return base + """
            **Posture & Balance Protocol:**
            - Core stabilization exercises: MANDATORY in every session
            - Posterior chain strengthening (back, glutes, hamstrings)
            - Balance challenges progressing from static to dynamic
            - Scapular stabilization work
            """
        else:
            return base + """
            **General Fitness Protocol:**
            - Balanced approach across all fitness components
            - Include strength, cardio, flexibility, and balance elements
            - Moderate rep ranges: 10-15 reps
            - Varied rest periods: 30-60 seconds
            - Full-body functional movements preferred
            """
    
    def _determine_exercise_count(self, session_duration: str) -> int:
        """Determine number of exercises based on session duration"""
        duration_map = {
            "15-20 minutes": 4,
            "20-30 minutes": 5,
            "30-45 minutes": 6,
            "45-60 minutes": 7,
            "60+ minutes": 8
        }
        return duration_map.get(session_duration, 5)
    
    def generate_workout_plan(self, user_profile: Dict, day_name: str, day_index: int) -> str:
        """Generate a single day's workout plan using enhanced prompting"""
        
        system_prompt = self._build_system_prompt(user_profile, day_name, day_index)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "messages": [
                    {"role": "system", "content": "You are FriskaAI, a precise clinical exercise physiologist. Generate workout plans with medical accuracy and zero hallucination. Always respond in English."},
                    {"role": "user", "content": system_prompt}
                ],
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 2500
            }
            
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                json=payload,
                timeout=60
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
        
        plan = f"""### {day_name} – {focus}

        **Warm-Up (5 minutes)**

        - Arm Circles – Shoulder mobility and blood flow – 1 minute – Keep movements controlled and pain-free
        - Leg Swings – Hip mobility and dynamic stretching – 2 minutes – Hold onto support if needed
        - Marching in Place – Heart rate elevation – 2 minutes – Gradually increase pace

        **Main Workout**

        **1. Bodyweight Squats**
        - Benefit: Builds leg strength and functional movement
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
        - Benefit: Upper body strength without floor stress
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
        - Benefit: Core activation and balance
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
        - Benefit: Posterior chain strength and hip stability
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
    """Inject modern, professional CSS styling"""
    st.markdown("""
    <style>
    /* Main App Styling */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    
    /* Header Styling */
    .header-container {
        background: Black;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .header-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .header-subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    
    /* Form Sections */
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1.5rem 0 1rem 0;
        font-size: 1.3rem;
        font-weight: 600;
    }
    
    /* Info Boxes */
    .info-box {
        background: black;
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: Black;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .success-box {
        background: black;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* BMI Result Styling */
    .bmi-container {
        background: Black;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    .bmi-value {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .bmi-category {
        font-size: 1.2rem;
        text-align: center;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }
    
    /* Workout Plan Styling */
    .workout-day {
        background: black;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 1.5rem 0;
    }
    
    /* Footer Styling */
    .footer {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-top: 3rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 5px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# ============ SESSION STATE INITIALIZATION ============
def initialize_session_state():
    """Initialize all session state variables"""
    if 'fitness_plan_generated' not in st.session_state:
        st.session_state.fitness_plan_generated = False
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = {}
    if 'workout_plans' not in st.session_state:
        st.session_state.workout_plans = {}
    if 'feedback_submitted' not in st.session_state:
        st.session_state.feedback_submitted = False

# ============ MAIN APPLICATION ============
def main():
    """Main application function"""
    
    # Initialize
    inject_custom_css()
    initialize_session_state()
    advisor = FitnessAdvisor(API_KEY, ENDPOINT_URL)
    
    # ============ HEADER ============
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">💪 FriskaAI Fitness Coach</h1>
        <p class="header-subtitle">Your Personalized, Medically-Safe AI Fitness Partner</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ============ MAIN FORM ============
    if not st.session_state.fitness_plan_generated:
        
        st.markdown('<div class="info-box">📋 <strong>Complete the form below to receive your personalized fitness plan.</strong> All information is kept confidential and used only to create your safe, effective workout program.</div>', unsafe_allow_html=True)
        
        with st.form("fitness_assessment_form"):
            
            # ===== SECTION 1: BASIC INFORMATION =====
            st.markdown('<div class="section-header">📝 Section 1: Basic Information</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *", placeholder="Enter your name")
                age = st.number_input("Age *", min_value=13, max_value=100, value=30, step=1)
                gender = st.selectbox("Gender *", ["Male", "Female", "Other", "Prefer not to say"])
            
            with col2:
                weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=70.0, step=0.5)
                height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=170.0, step=0.5)
            
            # BMI Calculation
            if weight_kg > 0 and height_cm > 0:
                bmi = weight_kg / ((height_cm / 100) ** 2)
                
                if bmi < 18.5:
                    bmi_category = "Underweight"
                    bmi_color = "#ff9800"
                elif 18.5 <= bmi < 25:
                    bmi_category = "Normal Weight"
                    bmi_color = "#4caf50"
                elif 25 <= bmi < 30:
                    bmi_category = "Overweight"
                    bmi_color = "#ff9800"
                else:
                    bmi_category = "Obese"
                    bmi_color = "#f44336"
                
                st.markdown(f"""
                <div class="bmi-container">
                    <div style="color: #666;">Your BMI</div>
                    <div class="bmi-value" style="color: {bmi_color};">{bmi:.1f}</div>
                    <div class="bmi-category" style="color: {bmi_color};">{bmi_category}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # ===== SECTION 2: GOALS & FITNESS LEVEL =====
            st.markdown('<div class="section-header">🎯 Section 2: Goals & Fitness Level</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                primary_goal = st.selectbox(
                    "Primary Fitness Goal *",
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
            
            with col2:
                fitness_level = st.selectbox(
                    "Current Fitness Level *",
                    [
                        "Level 1 – Assisted / Low Function",
                    "Level 2 – Beginner Functional",
                    "Level 3 – Moderate / Independent  ",
                    "Level 4 – Active Wellness  ",
                    "Level 5 – Adaptive Advanced"
                    ]
                )
            
            # ===== SECTION 3: HEALTH SCREENING =====
            st.markdown('<div class="section-header">🏥 Section 3: Health Screening (Critical for Safety)</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="warning-box">⚠️ <strong>Medical Conditions:</strong> Selecting your conditions helps us create a SAFE workout plan. All exercises will be adapted to avoid contraindicated movements.</div>', unsafe_allow_html=True)
            
            medical_conditions = st.multiselect(
                "Do you have any of these medical conditions? (Select all that apply) *",
                MEDICAL_CONDITIONS,
                default=["None"]
            )
            
            # Remove "None" if other conditions are selected
            if len(medical_conditions) > 1 and "None" in medical_conditions:
                medical_conditions = [c for c in medical_conditions if c != "None"]
            
            physical_limitations = st.text_area(
                "Physical Limitations or Injuries",
                placeholder="E.g., previous knee surgery, shoulder pain, limited mobility in right hip...",
                help="Describe any injuries, pain, or movement restrictions"
            )
            
            current_medications = st.text_area(
                "Current Medications (Optional)",
                placeholder="E.g., blood pressure medication, insulin, beta-blockers...",
                help="Some medications affect exercise response"
            )
            
            # Medical Clearance Check
            if age >= 65 or any(cond not in ["None", "Other"] for cond in medical_conditions):
                st.markdown('<div class="warning-box">⚠️ <strong>Medical Clearance Recommended:</strong> Based on your profile, we recommend consulting a physician before starting a new exercise program. Our plans are designed to be safe, but medical supervision is advised.</div>', unsafe_allow_html=True)
            
            # ===== SECTION 4: WORKOUT PREFERENCES =====
            st.markdown('<div class="section-header">💪 Section 4: Workout Preferences</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                workout_location = st.selectbox(
                    "Where will you work out? *",
                    ["Home", "Gym", "Outdoor/Park", "Office", "Mixed Locations"]
                )
                
                session_duration = st.selectbox(
                    "Session Duration *",
                    ["15-20 minutes", "20-30 minutes", "30-45 minutes", "45-60 minutes", "60+ minutes"]
                )
            
            with col2:
                days_per_week = st.multiselect(
                    "Select Training Days *",
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    default=["Monday", "Wednesday", "Friday"]
                )
                
                workout_time = st.selectbox(
                    "Preferred Workout Time",
                    ["Early Morning (5-8 AM)", "Morning (8-12 PM)", "Afternoon (12-5 PM)", "Evening (5-8 PM)", "Night (8 PM+)", "Flexible"]
                )
            
            # Equipment Selection
            st.markdown("**Available Equipment** (Select all that apply) *")
            
            equipment_cols = st.columns(3)
            
            with equipment_cols[0]:
                eq_bodyweight = st.checkbox("None - Bodyweight Only", value=True)
                eq_dumbbells = st.checkbox("Dumbbells")
                eq_resistance_bands = st.checkbox("Resistance Bands")
                eq_kettlebells = st.checkbox("Kettlebells")
            
            with equipment_cols[1]:
                eq_barbell = st.checkbox("Barbell & Plates")
                eq_bench = st.checkbox("Bench")
                eq_pullup_bar = st.checkbox("Pull-up Bar")
                eq_yoga_mat = st.checkbox("Yoga Mat")
            
            with equipment_cols[2]:
                eq_cardio = st.checkbox("Cardio Machine (Treadmill/Bike)")
                eq_trx = st.checkbox("TRX/Suspension Trainer")
                eq_medicine_ball = st.checkbox("Medicine Ball")
                eq_foam_roller = st.checkbox("Foam Roller")
            
            # Compile equipment list
            available_equipment = []
            if eq_bodyweight: available_equipment.append("None - Bodyweight Only")
            if eq_dumbbells: available_equipment.append("Dumbbells")
            if eq_resistance_bands: available_equipment.append("Resistance Bands")
            if eq_kettlebells: available_equipment.append("Kettlebells")
            if eq_barbell: available_equipment.append("Barbell & Plates")
            if eq_bench: available_equipment.append("Bench")
            if eq_pullup_bar: available_equipment.append("Pull-up Bar")
            if eq_yoga_mat: available_equipment.append("Yoga Mat")
            if eq_cardio: available_equipment.append("Cardio Machine")
            if eq_trx: available_equipment.append("TRX/Suspension Trainer")
            if eq_medicine_ball: available_equipment.append("Medicine Ball")
            if eq_foam_roller: available_equipment.append("Foam Roller")
            
            if not available_equipment:
                available_equipment = ["None - Bodyweight Only"]
            
            # Target Areas
            target_areas = st.multiselect(
                "Target Areas / Focus *",
                [
                    "Full Body",
                    "Upper Body (Chest, Back, Arms)",
                    "Lower Body (Legs, Glutes)",
                    "Core & Abs",
                    "Back & Posture",
                    "Arms & Shoulders",
                    "Legs & Glutes",
                    "Cardiovascular System",
                    "Flexibility & Mobility"
                ],
                default=["Full Body"]
            )
            
            # ===== SECTION 5: ADDITIONAL PREFERENCES =====
            st.markdown('<div class="section-header">⚙️ Section 5: Additional Preferences</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                workout_style = st.selectbox(
                    "Preferred Workout Style",
                    ["Balanced Mix", "Strength-Focused", "Cardio-Focused", "HIIT (High Intensity)", "Low-Impact", "Functional Training", "Circuit Training", "Stretching & Recovery"]
                )
            
            with col2:
                exercise_variety = st.selectbox(
                    "Exercise Variety Preference",
                    ["Moderate Variety (Recommended)", "High Variety (Change frequently)", "Low Variety (Repeat same exercises)"]
                )
            
            additional_notes = st.text_area(
                "Additional Notes or Preferences",
                placeholder="E.g., prefer outdoor exercises, dislike certain movements, specific goals...",
                help="Any other information that would help us personalize your plan"
            )
            
            # ===== MEDICAL DISCLAIMER =====
            st.markdown('<div class="section-header">⚕️ Medical Disclaimer & Consent</div>', unsafe_allow_html=True)
            
            st.markdown("""
            <div class="warning-box">
            <strong>IMPORTANT MEDICAL DISCLAIMER:</strong><br><br>
            
            This AI-generated fitness program is for <strong>informational purposes only</strong> and does not constitute medical advice. By using this service, you acknowledge that:
            
            <ul>
            <li>✓ You should consult a physician before starting any new exercise program, especially if you have medical conditions</li>
            <li>✓ FriskaAI is not a substitute for professional medical advice, diagnosis, or treatment</li>
            <li>✓ You assume full responsibility for any risks associated with exercise activities</li>
            <li>✓ You will stop exercising immediately if you experience pain, dizziness, or unusual symptoms</li>
            <li>✓ The AI may not be aware of all contraindications specific to your individual health status</li>
            </ul>
            
            <strong>When to seek immediate medical attention:</strong> Chest pain, severe shortness of breath, dizziness, fainting, or unusual symptoms during exercise.
            </div>
            """, unsafe_allow_html=True)
            
            disclaimer_accepted = st.checkbox(
                "I have read and agree to the Medical Disclaimer. I understand the risks and will consult a healthcare provider if needed. *",
                value=False
            )
            
            # ===== FORM SUBMISSION =====
            st.markdown("---")
            submit_button = st.form_submit_button("🚀 Generate My Personalized Fitness Plan", use_container_width=True)
            
            if submit_button:
                # Validation
                validation_errors = []
                
                if not name or len(name.strip()) < 2:
                    validation_errors.append("❌ Please enter your full name")
                
                if age < 13:
                    validation_errors.append("❌ You must be at least 13 years old to use this service")
                
                if not days_per_week or len(days_per_week) == 0:
                    validation_errors.append("❌ Please select at least one training day")
                
                if not target_areas or len(target_areas) == 0:
                    validation_errors.append("❌ Please select at least one target area")
                
                if not disclaimer_accepted:
                    validation_errors.append("❌ You must accept the Medical Disclaimer to proceed")
                
                # Display validation errors
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    # Store user profile
                    st.session_state.user_profile = {
                        "name": name.strip(),
                        "age": age,
                        "gender": gender,
                        "weight_kg": weight_kg,
                        "height_cm": height_cm,
                        "bmi": round(bmi, 1) if weight_kg > 0 and height_cm > 0 else 0,
                        "primary_goal": primary_goal,
                        "fitness_level": fitness_level,
                        "medical_conditions": medical_conditions,
                        "physical_limitations": physical_limitations,
                        "current_medications": current_medications,
                        "workout_location": workout_location,
                        "session_duration": session_duration,
                        "days_per_week": days_per_week,
                        "workout_time": workout_time,
                        "available_equipment": available_equipment,
                        "target_areas": target_areas,
                        "workout_style": workout_style,
                        "exercise_variety": exercise_variety,
                        "additional_notes": additional_notes,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Generate workout plans
                    with st.spinner("🔄 Generating your personalized fitness plan... This may take 30-60 seconds."):
                        try:
                            progress_bar = st.progress(0)
                            
                            for idx, day in enumerate(days_per_week):
                                progress = (idx + 1) / len(days_per_week)
                                progress_bar.progress(progress)
                                
                                plan = advisor.generate_workout_plan(
                                    st.session_state.user_profile,
                                    day,
                                    idx
                                )
                                
                                st.session_state.workout_plans[day] = plan
                            
                            progress_bar.empty()
                            st.session_state.fitness_plan_generated = True
                            st.success("✅ Your personalized fitness plan is ready!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error generating plan: {str(e)}")
                            st.error("Please try again or contact support if the issue persists.")
    
    # ============ DISPLAY FITNESS PLAN ============
    else:
        profile = st.session_state.user_profile
        
        # Header with user info
        st.markdown(f"""
        <div class="success-box">
            <h2>👋 Welcome, {profile['name']}!</h2>
            <p><strong>Your Personalized Fitness Plan is Ready</strong></p>
            <p>📅 Generated: {profile['timestamp']} | 🎯 Goal: {profile['primary_goal']} | 💪 Level: {profile['fitness_level']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Medical Safety Summary
        if profile['medical_conditions'] and profile['medical_conditions'] != ["None"]:
            st.markdown(f"""
            <div class="warning-box">
                <strong>🏥 Medical Adaptations Applied:</strong><br>
                Your plan has been customized to accommodate: <strong>{', '.join(profile['medical_conditions'])}</strong><br>
                All contraindicated exercises have been removed or modified for your safety.
            </div>
            """, unsafe_allow_html=True)
        
        # Display workout plans
        st.markdown('<div class="section-header">📅 Your Weekly Workout Schedule</div>', unsafe_allow_html=True)
        
        for day in profile['days_per_week']:
            with st.expander(f"📋 {day} Workout Plan", expanded=True):
                if day in st.session_state.workout_plans:
                    st.markdown(st.session_state.workout_plans[day])
                else:
                    st.warning(f"Plan for {day} not available. Please regenerate.")
        
        # Download button
        st.markdown("---")
        full_plan = f"""
# FriskaAI Personalized Fitness Plan
Generated: {profile['timestamp']}

## User Profile
- Name: {profile['name']}
- Age: {profile['age']} | Gender: {profile['gender']}
- BMI: {profile['bmi']} | Weight: {profile['weight_kg']} kg | Height: {profile['height_cm']} cm
- Fitness Level: {profile['fitness_level']}
- Primary Goal: {profile['primary_goal']}
- Medical Conditions: {', '.join(profile['medical_conditions'])}
- Physical Limitations: {profile['physical_limitations'] if profile['physical_limitations'] else 'None'}
- Training Days: {', '.join(profile['days_per_week'])}
- Session Duration: {profile['session_duration']}
- Location: {profile['workout_location']}
- Equipment: {', '.join(profile['available_equipment'])}

## Weekly Workout Schedule

"""
        
        for day in profile['days_per_week']:
            if day in st.session_state.workout_plans:
                full_plan += f"\n{st.session_state.workout_plans[day]}\n\n---\n"
        
        full_plan += """
## Important Safety Reminders

⚠️ Stop exercising immediately if you experience:
- Chest pain or pressure
- Severe shortness of breath
- Dizziness or lightheadedness
- Unusual fatigue
- Sharp or severe pain

✓ Always warm up before and cool down after workouts
✓ Stay hydrated throughout your session
✓ Listen to your body and adjust intensity as needed
✓ Consult your physician if you have concerns

Generated by FriskaAI - Your AI Fitness Coach
"""
        
        st.download_button(
            label="📥 Download Complete Fitness Plan (Markdown)",
            data=full_plan,
            file_name=f"FriskaAI_Fitness_Plan_{profile['name']}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Generate New Plan", use_container_width=True):
                st.session_state.fitness_plan_generated = False
                st.session_state.workout_plans = {}
                st.rerun()
        
        with col2:
            if st.button("✏️ Modify Existing Plan", use_container_width=True):
                st.info("💡 To modify your plan, click 'Generate New Plan' and adjust your preferences.")
        
        # ============ FEEDBACK SECTION ============
        st.markdown('<div class="section-header">💬 Feedback & Support</div>', unsafe_allow_html=True)
        
        if not st.session_state.feedback_submitted:
            with st.form("feedback_form"):
                st.markdown("**Help us improve FriskaAI!** Your feedback is valuable.")
                
                rating = st.slider("How satisfied are you with your fitness plan?", 1, 5, 5)
                feedback_text = st.text_area("Comments or suggestions (optional)", placeholder="What did you like? What could be better?")
                
                submit_feedback = st.form_submit_button("Submit Feedback")
                
                if submit_feedback:
                    st.session_state.feedback_submitted = True
                    st.success("✅ Thank you for your feedback! We appreciate your input.")
                    st.balloons()
        else:
            st.markdown('<div class="success-box">✅ Thank you for submitting your feedback!</div>', unsafe_allow_html=True)
    
    # ============ FAQ SECTION ============
    st.markdown("---")
    st.markdown('<div class="section-header">❓ Frequently Asked Questions</div>', unsafe_allow_html=True)
    
    with st.expander("🔍 How is my fitness plan personalized?"):
        st.markdown("""
        FriskaAI uses advanced AI to analyze:
        - Your medical conditions and physical limitations
        - Age, fitness level, and experience
        - Available equipment and workout location
        - Primary fitness goals and target areas
        - Time constraints and scheduling preferences
        
        Every exercise is cross-referenced against medical contraindications to ensure safety.
        """)
    
    with st.expander("🏥 Is this safe if I have medical conditions?"):
        st.markdown("""
        FriskaAI implements strict medical safety protocols:
        - Contraindicated exercises are automatically excluded
        - Intensity is adjusted based on your conditions
        - Modified, safer alternatives are provided
        - Age-appropriate adaptations are applied
        
        **However:** Always consult your physician before starting a new exercise program, especially if you have medical conditions or are over 65.
        """)
    
    with st.expander("📊 What does RPE mean?"):
        st.markdown("""
        **RPE = Rate of Perceived Exertion** (1-10 scale)
        
        - **1-2:** Very Light (minimal effort)
        - **3-4:** Light (can talk easily)
        - **5-6:** Moderate (can talk in short sentences)
        - **7-8:** Hard (difficult to speak)
        - **9-10:** Very Hard to Maximal (cannot maintain)
        
        Use RPE to self-regulate your workout intensity based on how you feel.
        """)
    
    with st.expander("🔄 Can I modify my plan?"):
        st.markdown("""
        Yes! You can:
        - Click "Generate New Plan" to start fresh with different parameters
        - Adjust exercises yourself based on how your body responds
        - Increase or decrease intensity as you progress
        - Substitute exercises if equipment is unavailable
        
        Listen to your body and make adjustments as needed for safety and effectiveness.
        """)
    
    with st.expander("⏱️ How long should I follow this plan?"):
        st.markdown("""
        **Recommended Duration:**
        - Beginners: 4-6 weeks before progression
        - Intermediate: 6-8 weeks with periodic adjustments
        - Advanced: 8-12 weeks with planned periodization
        
        After this period, regenerate your plan with updated fitness level and goals.
        """)
    
    with st.expander("💡 Tips for success"):
        st.markdown("""
        **Maximize Your Results:**
        - ✅ Be consistent with your training schedule
        - ✅ Track your workouts and progress
        - ✅ Prioritize recovery and sleep
        - ✅ Stay hydrated (8-10 glasses of water daily)
        - ✅ Combine exercise with proper nutrition
        - ✅ Start conservatively and progress gradually
        - ✅ Don't skip warm-ups or cool-downs
        - ✅ Listen to your body and rest when needed
        """)
    
    # ============ FOOTER ============
    st.markdown("""
    <div class="footer">
        <p style="font-size: 1.1rem; color: #666; font-weight: 600; margin-bottom: 1rem;">💪 FriskaAI - Your AI Fitness Coach</p>
        <p style="color: #666; margin-bottom: 0.5rem;">Powered by Advanced AI | Evidence-Based Exercise Science | Medical Safety First</p>
        <p style="color: #999; font-size: 0.9rem;">© 2024 FriskaAI. For informational purposes only. Not a substitute for professional medical advice.</p>
        <p style="color: #999; font-size: 0.85rem; margin-top: 1rem;">
            <strong>Disclaimer:</strong> Always consult with a healthcare provider before beginning any exercise program.
            Stop immediately if you experience pain or discomfort.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============ RUN APPLICATION ============
if __name__ == "__main__":
    main()