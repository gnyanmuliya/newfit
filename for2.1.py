import streamlit as st
import requests
from typing import Dict, List, Optional, Set
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

# === COMPLETE REPLACEMENT FOR FitnessAdvisor CLASS ===

class FitnessAdvisor:
    """Enhanced fitness planning engine with 90%+ accuracy target through improved prompting and validation"""
    
    def __init__(self, api_key: str, endpoint_url: str):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.weekly_exercises_used = {
            'warmup': set(),
            'main': set(),
            'cooldown': set()
        }
    
    def reset_weekly_tracker(self):
        """Reset exercise tracker for new week generation"""
        self.weekly_exercises_used = {
            'warmup': set(),
            'main': set(),
            'cooldown': set()
        }
    
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
        Build ultra-precise system prompt for 90%+ accuracy
        Enhanced with strict constraints, explicit examples, and validation requirements
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
        
        # Determine focus with day-specific variation strategy
        focus = self._get_day_specific_focus(day_name, day_index, target_areas, primary_goal)
        
        # Build comprehensive prompt sections
        prompt_parts = []
        
        # ==================== SECTION 0: ENHANCED IDENTITY & MISSION ====================
        prompt_parts.append("""You are FriskaAI, an expert clinical exercise physiologist (ACSM-CEP) with 15+ years of experience in personalized program design. Your reputation depends on creating workout plans that are:
1. MEDICALLY SAFE (zero contraindicated exercises)
2. GOAL-ALIGNED (90%+ relevance to user's primary goal)
3. HIGHLY VARIED (zero exercise repetition within the week)
4. SCIENTIFICALLY SOUND (evidence-based exercise selection and programming)

You MUST respond ONLY in English. Every workout you generate is evaluated by medical professionals for safety and efficacy.

**CRITICAL PERFORMANCE METRICS YOU WILL BE EVALUATED ON:**
- Medical Safety: 100% (automatic fail if any contraindicated exercise included)
- Goal Alignment: 90%+ (exercises must directly support primary goal)
- Exercise Variety: 90%+ (no repetition within 7-day period)
- Structural Completeness: 100% (all sections mandatory)
- Format Compliance: 95%+ (strict markdown formatting)
""")
        
        # ==================== SECTION 1: USER PROFILE ====================
        profile_section = f"""
**1. USER PROFILE & FITNESS PARAMETERS (STRICTLY ENFORCE):**

**Basic Information:**
- Name: {name}
- Age: {age} years old
- Gender: {gender}
- Current Fitness Level: {fitness_level}
- Primary Fitness Goal: {primary_goal}
- Session Duration: {session_duration}
- Workout Location: {location}

**TODAY'S FOCUS: {day_name} - {focus}**
This is day {day_index + 1} of the weekly program. Each day MUST have distinct exercises.

**Medical & Physical Status (HIGHEST PRIORITY):**
- Medical Conditions: {', '.join(medical_conditions)}
- Physical Limitations: {physical_limitations if physical_limitations else 'None reported'}
- Safety Status: {'HIGH RISK - Medical adaptations MANDATORY' if medical_conditions != ['None'] else 'Standard precautions apply'}

**Available Equipment (STRICT CONSTRAINT):**
{', '.join(available_equipment)}
**RULE: You may ONLY use exercises possible with the equipment listed above. No exceptions.**
"""
        prompt_parts.append(profile_section)
        
        # ==================== SECTION 2: ENHANCED MEDICAL SAFETY ====================
        condition_guidelines = self._get_condition_guidelines(medical_conditions)
        
        if medical_conditions and medical_conditions != ["None"]:
            safety_section = f"""
**2. MEDICAL SAFETY PROTOCOL (ABSOLUTE REQUIREMENTS - ZERO TOLERANCE):**

**Condition-Specific Guidelines:**
{condition_guidelines}

**MANDATORY SAFETY CHECKLIST (VERIFY BEFORE FINALIZING):**
1. ✓ Every exercise cross-referenced against contraindication list
2. ✓ Zero exercises from "Contraindicated" category included
3. ✓ All exercises use "Modified/Safer" alternatives when available
4. ✓ RPE limits respect medical condition intensity caps
5. ✓ Safety cues specifically address user's medical conditions

**FAILURE CONDITION:** Including even ONE contraindicated exercise = complete plan rejection

**ADDITIONAL SAFETY RULES:**
- If user has Hypertension: NO breath-holding, NO maximal effort, NO overhead pressing without breathing cues
- If user has Osteoarthritis: NO high-impact movements, pain-free range only, prefer low-impact alternatives
- If user has Diabetes: Monitor intensity carefully, avoid extreme blood sugar fluctuations
- If user has Back Pain: Neutral spine emphasis, NO loaded flexion, core stability priority
- If user has Cardiovascular Disease: Conservative intensity, extended warm-up (minimum 7 minutes)
- If user aged 60+: NO plyometrics in first 8 weeks, balance work mandatory, fall prevention priority
"""
        else:
            safety_section = """
**2. GENERAL SAFETY PROTOCOL (MANDATORY):**
- Progressive overload: Increase difficulty gradually across weeks, not days
- All exercises appropriate for age and fitness level
- Proper warm-up (5-7 min) and cool-down (5-7 min) non-negotiable
- Clear safety cues for injury prevention
- Form quality always prioritized over load/volume
"""
        prompt_parts.append(safety_section)
        
        # ==================== SECTION 3: EXERCISE VARIETY ENFORCEMENT ====================
        used_exercises = self._format_used_exercises()
        variety_section = f"""
**3. EXERCISE VARIETY REQUIREMENTS (STRICT NO-REPETITION POLICY):**

**WEEKLY VARIETY MANDATE:**
This is {day_name} (Day {day_index + 1}). You MUST ensure ZERO exercise repetition across the entire week.

**Exercises Already Used This Week:**
{used_exercises}

**ABSOLUTE RULES:**
- Do NOT use ANY exercise listed above in today's warm-up, main workout, or cool-down
- Each day must have completely different exercises
- Similar movements are allowed ONLY if significantly modified (e.g., "Push-ups" vs "Incline Push-ups" vs "Diamond Push-ups")
- Warm-up variety: Use different mobility patterns each day (Day 1: circles, Day 2: swings, Day 3: rotations)
- Cool-down variety: Rotate between static stretches, dynamic stretches, breathing exercises, yoga poses

**CREATIVITY REQUIREMENT:**
If running low on exercise options, use these variation strategies:
- Change tempo (slow eccentric, pause at bottom, explosive concentric)
- Change stance (wide, narrow, staggered, split)
- Change equipment (if multiple available)
- Change angle (incline, decline, horizontal)
- Change grip (wide, narrow, neutral, pronated, supinated)
- Unilateral vs bilateral variations
"""
        prompt_parts.append(variety_section)
        
        # ==================== SECTION 4: AGE-ADAPTIVE RULES ====================
        age_rules = self._get_age_adaptations(age, medical_conditions)
        prompt_parts.append(age_rules)
        
        # ==================== SECTION 5: FITNESS LEVEL ADAPTATION ====================
        level_rules = self._get_fitness_level_rules(fitness_level)
        prompt_parts.append(level_rules)
        
        # ==================== SECTION 6: ENHANCED GOAL-SPECIFIC PROGRAMMING ====================
        goal_rules = self._get_enhanced_goal_rules(primary_goal, focus, day_index)
        prompt_parts.append(goal_rules)
        
        # ==================== SECTION 7: WORKOUT STRUCTURE WITH EXAMPLES ====================
        exercise_count = self._determine_exercise_count(session_duration)
        structure_rules = f"""
**7. MANDATORY WORKOUT STRUCTURE (ZERO FLEXIBILITY ON FORMAT):**

**YOU MUST GENERATE EXACTLY THIS STRUCTURE. MISSING ANY ELEMENT = INCOMPLETE PLAN.**

**SECTION A: WARM-UP (5-7 minutes) - MANDATORY - 3-4 MOVEMENTS**

**WARM-UP RULES:**
- MUST be mobility and activation ONLY (no strength/resistance work)
- MUST prepare the body specifically for {focus}
- MUST use different movements than previous days this week
- PROHIBITED in warm-up: Squats, push-ups, planks, lunges, burpees, any loaded exercises
- REQUIRED in warm-up: Dynamic stretches, joint circles, light cardio, activation drills

**GOOD WARM-UP EXAMPLES for {focus}:**
{self._get_warmup_examples(focus)}

**SECTION B: MAIN WORKOUT - MANDATORY - {exercise_count} EXERCISES**

**MAIN WORKOUT RULES:**
- MUST include exactly {exercise_count} exercises
- MUST prioritize {focus} (60-70% of exercises target this area)
- MUST align with {primary_goal} goal
- MUST alternate muscle groups/movement patterns when possible
- MUST NOT repeat any exercises from this week
- Each exercise MUST include ALL these fields:
  * Exercise Name (clear and specific)
  * Benefit (how it supports {primary_goal})
  * How to Perform (3-5 detailed steps)
  * Sets × Reps (based on goal and fitness level)
  * Intensity (RPE X-Y range)
  * Rest Period (seconds or minutes)
  * Safety Cue (specific to user's age/conditions/limitations)

**EXERCISE SELECTION PRIORITY for {primary_goal}:**
{self._get_exercise_selection_guidance(primary_goal, focus)}

**SECTION C: COOL-DOWN (5-7 minutes) - MANDATORY - 3-4 MOVEMENTS**

**COOL-DOWN RULES:**
- MUST be stretching, breathing, and recovery ONLY
- MUST NOT include any strength exercises
- MUST target areas worked in main workout
- MUST use different stretches than previous days
- PROHIBITED in cool-down: Planks, exercises requiring strength effort
- REQUIRED in cool-down: Static stretches (30-60 sec holds), breathing exercises, light yoga poses

**GOOD COOL-DOWN EXAMPLES for {focus}:**
{self._get_cooldown_examples(focus, age)}

**MANDATORY FORMATTING TEMPLATE:**

{day_name} – {focus} Focus
Warm-Up (5-7 minutes)

[Movement Name] – [Brief purpose] – [Duration/Reps] – [Safety note]
[Movement Name] – [Brief purpose] – [Duration/Reps] – [Safety note]
[Movement Name] – [Brief purpose] – [Duration/Reps] – [Safety note]
[Movement Name] – [Brief purpose] – [Duration/Reps] – [Safety note]

Main Workout (Target: {focus})
1. [Exercise Name]

Benefit: [Specific benefit for {primary_goal}]
How to Perform:

[Detailed step]
[Detailed step]
[Detailed step]


Sets × Reps: [X × Y]
Intensity: RPE [X-Y]
Rest: [X seconds/minutes]
Safety Cue: [Specific to user profile]

[Repeat for all {exercise_count} exercises]
Cool-Down (5-7 minutes)

[Stretch Name] – [Target area] – [Duration] – [Safety note]
[Stretch Name] – [Target area] – [Duration] – [Safety note]
[Stretch Name] – [Target area] – [Duration] – [Safety note]
[Stretch Name] – [Target area] – [Duration] – [Safety note]

"""
        prompt_parts.append(structure_rules)
        
        # ==================== SECTION 8: EQUIPMENT CONSTRAINTS ====================
        equipment_rules = f"""
**8. EQUIPMENT CONSTRAINTS (STRICTLY ENFORCE):**

**Available Equipment ONLY:**
{', '.join(available_equipment)}

**SELECTION RULES:**
- If "None - Bodyweight Only": ALL exercises must be performable with zero equipment
  * Allowed: Bodyweight exercises, household items (chair, wall, towel, water bottles)
  * NOT allowed: Dumbbells, barbells, machines, specialized equipment
  
- If equipment listed: You MAY use that equipment but also bodyweight alternatives
  * Prefer compound movements that maximize equipment efficiency
  * Balance equipment-based and bodyweight exercises

**EQUIPMENT-APPROPRIATE EXERCISES:**
{self._get_equipment_appropriate_exercises(available_equipment, focus)}
"""
        prompt_parts.append(equipment_rules)
        
        # ==================== SECTION 9: INTENSITY & VOLUME PRECISION ====================
        intensity_rules = self._get_precise_intensity_rules(fitness_level, primary_goal, age, medical_conditions)
        prompt_parts.append(intensity_rules)
        
        # ==================== SECTION 10: OUTPUT QUALITY CHECKLIST ====================
        quality_section = f"""
**10. PRE-SUBMISSION QUALITY CHECKLIST (MANDATORY VERIFICATION):**

Before submitting your workout plan, verify EVERY item:

**STRUCTURAL COMPLETENESS (100% Required):**
- [ ] Warm-up section included with 3-4 movements
- [ ] Main workout included with exactly {exercise_count} exercises
- [ ] Cool-down section included with 3-4 movements
- [ ] Day title formatted as: ### {day_name} – {focus} Focus

**MEDICAL SAFETY (100% Required):**
- [ ] Zero contraindicated exercises for: {', '.join(medical_conditions)}
- [ ] All exercises appropriate for age {age}
- [ ] RPE limits respect medical conditions
- [ ] Safety cues address specific user concerns

**GOAL ALIGNMENT (90%+ Required):**
- [ ] At least {int(exercise_count * 0.6)} exercises directly target {primary_goal}
- [ ] Exercise selection matches {focus} focus
- [ ] Rep ranges appropriate for {primary_goal}
- [ ] Rest periods appropriate for {primary_goal}

**VARIETY (90%+ Required):**
- [ ] Zero exercises repeated from previous days
- [ ] Warm-up uses different movements than before
- [ ] Main exercises all unique within week
- [ ] Cool-down uses different stretches than before

**EQUIPMENT COMPLIANCE (100% Required):**
- [ ] All exercises possible with: {', '.join(available_equipment)}
- [ ] Zero exercises requiring unavailable equipment

**FORMAT COMPLIANCE (95%+ Required):**
- [ ] Markdown formatting correct (###, **, numbered lists)
- [ ] All exercise fields included (Benefit, How to Perform, Sets×Reps, RPE, Rest, Safety)
- [ ] No conversational filler text
- [ ] Professional, concise tone

**ACCURACY TARGET: If you cannot confidently check ALL boxes above, revise your plan before submitting.**
"""
        prompt_parts.append(quality_section)
        
        # ==================== SECTION 11: FINAL TASK DIRECTIVE ====================
        if is_modification:
            task = f"""
**YOUR TASK:** Generate a MODIFIED workout plan for {day_name} based on this request: "{modification_request}"

Maintain all safety protocols and quality standards while incorporating the requested changes.
"""
            if original_plan_context:
                task += f"\n**Original Plan:**\n{original_plan_context}\n"
        else:
            task = f"""
**YOUR TASK:** Generate a COMPLETE, HIGH-ACCURACY workout plan for {day_name} focusing on {focus}.

**SUCCESS CRITERIA:**
- Medical Safety: 100%
- Goal Alignment: 90%+
- Exercise Variety: 90%+
- Structural Completeness: 100%
- Format Compliance: 95%+

**REMEMBER:** This plan will be evaluated against strict criteria. Quality and safety are non-negotiable.
"""
        
        prompt_parts.append(task)
        
        return "\n".join(prompt_parts)
    
    def _get_day_specific_focus(self, day_name: str, day_index: int, target_areas: List[str], primary_goal: str) -> str:
        """Determine day-specific focus with intelligent variation"""
        
        # If multiple target areas, rotate through them
        if len(target_areas) > 1:
            return target_areas[day_index % len(target_areas)]
        
        # If single target area, create variation within that area
        single_target = target_areas[0]
        
        # For Full Body, create day-specific variations
        if "Full Body" in single_target:
            variations = [
                "Full Body (Lower Focus)",
                "Full Body (Upper Focus)",
                "Full Body (Core Focus)",
                "Full Body (Balanced)",
                "Full Body (Cardio Focus)",
                "Full Body (Strength Focus)",
                "Full Body (Mobility Focus)"
            ]
            return variations[day_index % len(variations)]
        
        return single_target
    
    def _format_used_exercises(self) -> str:
        """Format already-used exercises for prompt"""
        if not any(self.weekly_exercises_used.values()):
            return "**No exercises used yet** (This is the first day of the week)"
        
        formatted = []
        
        if self.weekly_exercises_used['warmup']:
            formatted.append(f"**Warm-up exercises used:** {', '.join(self.weekly_exercises_used['warmup'])}")
        
        if self.weekly_exercises_used['main']:
            formatted.append(f"**Main workout exercises used:** {', '.join(self.weekly_exercises_used['main'])}")
        
        if self.weekly_exercises_used['cooldown']:
            formatted.append(f"**Cool-down exercises used:** {', '.join(self.weekly_exercises_used['cooldown'])}")
        
        return "\n".join(formatted) if formatted else "**No exercises tracked yet**"
    
    def _get_warmup_examples(self, focus: str) -> str:
        """Provide focus-specific warm-up examples"""
        examples = {
            "Upper Body": "- Arm circles (forward/backward)\n- Shoulder rolls\n- Torso twists\n- Cat-cow stretches\n- Wrist circles\n- Neck mobility",
            "Lower Body": "- Leg swings (front-back, side-side)\n- Hip circles\n- Ankle mobility\n- Walking knee hugs\n- Calf raises\n- Bodyweight good mornings",
            "Core": "- Standing torso twists\n- Side bends\n- Hip circles\n- Cat-cow\n- Standing knee to elbow\n- Marching in place",
            "Full Body": "- Jumping jacks (or low-impact alternative)\n- Arm circles + leg swings\n- Torso rotations\n- Hip circles\n- March in place\n- Dynamic stretches"
        }
        
        for key in examples:
            if key.lower() in focus.lower():
                return examples[key]
        
        return examples["Full Body"]
    
    def _get_cooldown_examples(self, focus: str, age: int) -> str:
        """Provide focus and age-appropriate cool-down examples"""
        floor_based = age < 60
        
        if "Upper Body" in focus:
            if floor_based:
                return "- Child's pose (90 sec)\n- Chest doorway stretch (60 sec each side)\n- Shoulder cross-body stretch (60 sec each)\n- Tricep overhead stretch (60 sec each)\n- Upper back stretch\n- Deep breathing (2 min)"
            else:
                return "- Standing chest stretch (60 sec)\n- Shoulder cross-body stretch (60 sec each)\n- Tricep overhead stretch (60 sec each)\n- Wall-supported upper back stretch\n- Seated deep breathing (2 min)"
        
        elif "Lower Body" in focus:
            if floor_based:
                return "- Seated hamstring stretch (90 sec each)\n- Figure-4 hip stretch (90 sec each)\n- Lying quad stretch (60 sec each)\n- Butterfly stretch (90 sec)\n- Child's pose (60 sec)\n- Deep breathing"
            else:
                return "- Standing hamstring stretch (90 sec each)\n- Standing quad stretch (90 sec each)\n- Hip flexor stretch (90 sec each)\n- Calf stretch (60 sec each)\n- Seated deep breathing"
        
        else:
            if floor_based:
                return "- Child's pose (90 sec)\n- Spinal twist (60 sec each side)\n- Hamstring stretch (60 sec each)\n- Hip flexor stretch (60 sec each)\n- Cat-cow stretches (1 min)\n- Deep breathing (2 min)"
            else:
                return "- Standing full body stretch (60 sec)\n- Seated spinal twist (60 sec each)\n- Standing hamstring stretch (60 sec each)\n- Wall-supported chest stretch\n- Deep breathing exercises (3 min)"
    
    def _get_enhanced_goal_rules(self, primary_goal: str, focus: str, day_index: int) -> str:
        """Enhanced goal-specific rules with explicit exercise guidance"""
        base = f"**6. GOAL-SPECIFIC PROGRAMMING (PRIMARY GOAL: {primary_goal}):**\n\n"
        
        if "Weight Loss" in primary_goal or "weight loss" in primary_goal.lower():
            return base + f"""
**Weight Loss Protocol (High Caloric Expenditure):**

**Exercise Selection Priority:**
1. Compound, multi-joint movements (squats, lunges, push-ups, rows)
2. Metabolic conditioning exercises (mountain climbers, burpees, high knees)
3. Circuit-style training (minimal rest between exercises)
4. Full-body movements over isolation exercises

**Programming Parameters:**
- Rep Range: 12-20 reps per set (muscular endurance zone)
- Sets: 3-4 sets per exercise
- Rest Periods: 30-45 seconds (maintain elevated heart rate)
- Tempo: Moderate to fast (maintain intensity)
- Circuit option: Perform exercises back-to-back, rest after full circuit

**Exercise Examples to PRIORITIZE:**
- Squats, lunges, step-ups (lower body compound)
- Push-ups, rows, overhead presses (upper body compound)
- Mountain climbers, burpees, jumping jacks (metabolic)
- Plank variations, bicycle crunches (core engagement)

**Today's Focus ({focus}):** At least 70% of exercises should target {focus} while maximizing calorie burn.
"""
        
        elif "Muscle Gain" in primary_goal or "muscle" in primary_goal.lower() or "Hypertrophy" in primary_goal:
            return base + f"""
**Muscle Gain / Hypertrophy Protocol:**

**Exercise Selection Priority:**
1. Progressive resistance exercises (add weight/difficulty weekly)
2. Compound movements with good muscle tension
3. Controlled tempo emphasizing eccentric phase
4. Adequate volume (total sets × reps)

**Programming Parameters:**
- Rep Range: 6-12 reps per set (hypertrophy zone)
- Sets: 3-4 sets per exercise
- Rest Periods: 60-90 seconds (allow partial recovery)
- Tempo: 2-0-1-0 or 3-0-1-0 (slow eccentric, explosive concentric)
- Time Under Tension: 40-60 seconds per set

**Exercise Examples to PRIORITIZE:**
- Loaded squats, Romanian deadlifts, Bulgarian split squats
- Bench press, dumbbell presses, weighted push-ups
- Pull-ups, rows, lat pulldowns
- Overhead presses, lateral raises
- Bicep curls, tricep extensions, calf raises

**Today's Focus ({focus}):** Choose exercises that load {focus} muscles effectively with progressive resistance.
"""
        
        elif "Strength" in primary_goal or "strength" in primary_goal.lower():
            return base + f"""
**Strength Building Protocol (Neurological Adaptation):**

**Exercise Selection Priority:**
1. Compound lifts (squats, deadlifts, presses, rows)
2. Bilateral movements before unilateral
3. Exercises allowing progressive load increases
4. Focus on maximal force production

**Programming Parameters:**
- Rep Range: 4-8 reps per set (strength zone)
- Sets: 3-5 sets per exercise
- Rest Periods: 90-180 seconds (full recovery for max effort)
- Tempo: Controlled eccentric, explosive concentric
- Load: 70-85% of perceived max (RPE 7-8)

**Exercise Examples to PRIORITIZE:**
- Barbell/Dumbbell squats, front squats, goblet squats
- Deadlifts, Romanian deadlifts, single-leg deadlifts
- Bench press, overhead press, push-ups (weighted if possible)
- Pull-ups, rows, inverted rows
- Heavy carries, farmer's walks

**Today's Focus ({focus}):** Select 2-3 primary strength exercises for {focus}, then 2-3 accessory movements.
"""
        
        elif "Cardiovascular" in primary_goal or "cardio" in primary_goal.lower() or "Endurance" in primary_goal:
            return base + f"""
**Cardiovascular Fitness / Endurance Protocol:**

**Exercise Selection Priority:**
1. Continuous movement patterns (running, cycling movements)
2. Full-body dynamic exercises
3. Interval training (mix high/moderate intensity)
4. Exercises that elevate heart rate sustainably

**Programming Parameters:**
- Rep Range: 15-25 reps per set OR time-based (30-60 sec)
- Sets: 2-4 sets per exercise
- Rest Periods: 15-30 seconds (keep heart rate elevated)
- Tempo: Moderate to fast pace
- Heart Rate Target: 60-80% of max (based on age)

**Exercise Examples to PRIORITIZE:**
- High knees, butt kicks, mountain climbers
- Jump rope, jumping jacks, burpees
- Step-ups, box jumps, lateral hops
- Rowing motions, battle ropes
- Plank jacks, bicycle crunches

**Today's Focus ({focus}):** Create a circuit targeting {focus} with cardio emphasis. Mix steady-state and intervals.
"""
        
        elif "Flexibility" in primary_goal or "Mobility" in primary_goal:
            return base + f"""
**Flexibility & Mobility Protocol:**

**Exercise Selection Priority:**
1. Dynamic mobility drills (full range of motion)
2. Active stretching (moving through stretch)
3. Joint mobilization exercises
4. Flexibility-focused strength work

**Programming Parameters:**
- Dynamic Stretches: 10-15 reps per movement
- Static Stretches: 30-60 second holds
- Sets: 2-3 rounds through mobility sequence
- Rest: Minimal (transition between movements)
- Focus: Pain-free, gradual range of motion increases

**Exercise Examples to PRIORITIZE:**
- Leg swings, hip circles, arm circles
- Cat-cow, thread the needle, world's greatest stretch
- 90/90 hip switches, seated spinal twists
- Deep squat holds, cossack squats
- Yoga flows (downward dog to cobra)
- Static stretches for all major muscle groups

**Today's Focus ({focus}):** Dedicate majority of workout to mobility work for {focus}, include gentle strengthening.
"""
        
        elif "Rehabilitation" in primary_goal or "rehab" in primary_goal.lower() or "Recovery" in primary_goal:
            return base + f"""
**Rehabilitation & Recovery Protocol (CONSERVATIVE APPROACH):**

**Exercise Selection Priority:**
1. PAIN-FREE movement only (never work through pain)
2. Low-load, high-control exercises
3. Stabilization and activation work
4. Gradual progression (weeks, not days)

**Programming Parameters:**
- Rep Range: 10-15 reps (control emphasis)
- Sets: 2-3 sets per exercise
- Rest Periods: 60-90 seconds
- Tempo: SLOW and controlled (3-0-3-0)
- RPE: Maximum 3-5 (light to moderate effort only)

**Exercise Examples to PRIORITIZE:**
- Gentle range-of-motion exercises
- Isometric holds (plank variations, wall sits)
- Resistance band exercises (light resistance)
- Balance and proprioception work
- Core stabilization (bird dog, dead bug)
- Supported movements (wall push-ups, assisted squats)

**Today's Focus ({focus}):** Ultra-conservative approach to {focus}. Emphasize movement quality over quantity.

**CRITICAL:** All exercises must be pain-free. If user reports sharp pain, reduce intensity or skip exercise.
"""
        
        elif "Posture" in primary_goal or "Balance" in primary_goal:
            return base + f"""
**Posture Correction & Balance Protocol:**

**Exercise Selection Priority:**
1. Posterior chain strengthening (back, glutes, hamstrings)
2. Core stabilization (anti-rotation, anti-extension)
3. Balance challenges (single-leg work, unstable surfaces)
4. Scapular stabilization and control

**Programming Parameters:**
- Rep Range: 10-15 reps per set
- Sets: 2-3 sets per exercise
- Rest: 45-60 seconds
- Tempo: Slow and controlled
- Balance holds: 30-60 seconds per side

**Exercise Examples to PRIORITIZE:**
- Rows (all variations), reverse flys, face pulls
- Glute bridges, hip thrusts, deadlifts
- Planks (front, side), bird dogs, dead bugs
- Single-leg exercises (single-leg deadlifts, pistol squats, step-ups)
- Balance work (single-leg stands, tandem stance, BOSU work)
- Wall angels, band pull-aparts, YTWs

**Today's Focus ({focus}):** Include mandatory balance work + {focus} postural exercises. Minimum 2 single-leg exercises.
"""
        
        else:  # General Fitness
            return base + f"""
**General Fitness Protocol (Balanced Development):**

**Exercise Selection Priority:**
1. Balance across all fitness components (strength, cardio, flexibility, balance)
2. Functional movement patterns
3. Variety to prevent boredom
4. Progressive difficulty over weeks

**Programming Parameters:**
- Rep Range: 10-15 reps per set (moderate zone)
- Sets: 3 sets per exercise
- Rest: 30-60 seconds
- Tempo: Controlled (2-0-2-0)
- Mix strength, cardio, mobility in each session

**Exercise Examples to INCLUDE:**
- Compound strength: Squats, push-ups, rows, lunges
- Cardio bursts: High knees, jumping jacks, mountain climbers
- Core work: Planks, bicycle crunches, Russian twists
- Balance: Single-leg exercises, stability challenges
- Mobility: Dynamic stretches, yoga poses

**Today's Focus ({focus}):** Create balanced workout with {focus} emphasis, but include elements from all fitness domains.
"""
    
    # === CONTINUATION FROM _get_exercise_selection_guidance ===

    def _get_exercise_selection_guidance(self, primary_goal: str, focus: str) -> str:
        """Provide explicit exercise selection guidance"""
        return f"""
**For {primary_goal} goal targeting {focus}:**

1. **Primary Exercises (60-70% of workout):** These MUST directly target {focus} and support {primary_goal}
2. **Secondary Exercises (20-30%):** Supporting muscle groups for balanced development
3. **Tertiary Exercises (10%):** Mobility, balance, or corrective exercises

**Exercise Quality Checklist:**
- ✓ Appropriate for available equipment
- ✓ Matches fitness level difficulty
- ✓ Safe for medical conditions
- ✓ Aligned with primary goal
- ✓ NOT repeated from previous days this week
- ✓ Teaches proper movement patterns
- ✓ Scalable (can be made easier or harder)
"""

    def _get_equipment_appropriate_exercises(self, available_equipment: List[str], focus: str) -> str:
        """Provide equipment-specific exercise suggestions"""
        equipment_str = ', '.join(available_equipment)
        
        if "None - Bodyweight Only" in equipment_str or not available_equipment:
            return f"""
**BODYWEIGHT-ONLY EXERCISES for {focus}:**

**Upper Body (Bodyweight):**
- Push-ups (standard, wide, diamond, decline, incline)
- Pike push-ups, pseudo planche push-ups
- Inverted rows (using table/sturdy furniture)
- Tricep dips (chair/bench)
- Plank variations, side planks

**Lower Body (Bodyweight):**
- Squats (bodyweight, jump, pistol, Bulgarian split)
- Lunges (forward, reverse, walking, curtsy, lateral)
- Step-ups (using stairs/sturdy box)
- Glute bridges, single-leg bridges
- Calf raises (single and double leg)
- Wall sits

**Core (Bodyweight):**
- Planks (front, side, RKC, weighted with backpack)
- Dead bugs, bird dogs, hollow body holds
- Mountain climbers, bicycle crunches
- Russian twists, leg raises
- Superman holds, swimmer kicks

**Cardio (Bodyweight):**
- High knees, butt kicks, jumping jacks
- Burpees, mountain climbers
- Jump squats, jump lunges
- Skater hops, lateral bounds
- Sprint in place, bear crawls
"""
        
        elif "Dumbbells" in equipment_str or "Dumbbell" in equipment_str:
            return f"""
**DUMBBELL EXERCISES for {focus}:**

**Upper Body (Dumbbells):**
- Dumbbell bench press, chest flys
- Shoulder press, lateral raises, front raises
- Bent-over rows, single-arm rows
- Bicep curls (standard, hammer, concentration)
- Tricep extensions, tricep kickbacks
- Dumbbell pullovers

**Lower Body (Dumbbells):**
- Goblet squats, dumbbell front squats
- Romanian deadlifts, single-leg deadlifts
- Dumbbell lunges (forward, reverse, walking)
- Bulgarian split squats with dumbbells
- Dumbbell step-ups
- Calf raises holding dumbbells

**Core (Dumbbells):**
- Dumbbell Russian twists
- Weighted sit-ups/crunches
- Dumbbell side bends
- Dumbbell wood chops
- Renegade rows

**Plus ALL bodyweight exercises listed above**
"""
        
        elif "Resistance Bands" in equipment_str:
            return f"""
**RESISTANCE BAND EXERCISES for {focus}:**

**Upper Body (Bands):**
- Band chest press, chest flys
- Band rows, face pulls
- Band shoulder press, lateral raises
- Band bicep curls, tricep extensions
- Band pull-aparts, YTWs

**Lower Body (Bands):**
- Band squats, band deadlifts
- Band lateral walks, monster walks
- Band leg press (lying down)
- Band kickbacks, leg curls
- Band hip abductions/adductions

**Core (Bands):**
- Band pallof press (anti-rotation)
- Band wood chops
- Band dead bugs
- Band crunches

**Plus ALL bodyweight exercises listed above**
"""
        
        elif "Gym Access" in equipment_str or "Full Gym" in equipment_str:
            return f"""
**FULL GYM EXERCISES for {focus}:**

You have access to barbells, machines, cables, and all equipment. Prioritize:

**Compound Movements:**
- Barbell squats, deadlifts, bench press, overhead press
- Pull-ups, chin-ups, dips
- Barbell rows, T-bar rows
- Leg press, hack squats

**Isolation & Accessory:**
- Cable movements (all angles)
- Machine exercises (for safety and control)
- Dumbbell work (unilateral training)
- Specialty bars and attachments

**Plus bodyweight and mobility work**
"""
        
        else:
            return f"""
**MIXED EQUIPMENT EXERCISES for {focus}:**

Based on available equipment: {equipment_str}

Use a combination of:
1. Primary equipment listed for main strength work
2. Bodyweight exercises for metabolic conditioning
3. Household items (chairs, water bottles, towels) for assistance

**Strategy:** Maximize equipment efficiency by using compound movements that work multiple muscle groups.
"""

    def _get_precise_intensity_rules(self, fitness_level: str, primary_goal: str, age: int, medical_conditions: List[str]) -> str:
        """Provide precise intensity guidelines based on all factors"""
        
        # Determine base RPE ranges
        if "Level 1" in fitness_level or "Beginner" in fitness_level:
            base_rpe = "4-6 (Light to Moderate)"
            volume_guidance = "2-3 sets per exercise, focus on form mastery"
        elif "Level 2" in fitness_level or "level 2" in fitness_level.lower():
            base_rpe = "5-7 (Moderate)"
            volume_guidance = "3 sets per exercise, gradual load increases"
        elif "Level 3" in fitness_level or "Intermediate" in fitness_level:
            base_rpe = "6-8 (Moderate to Hard)"
            volume_guidance = "3-4 sets per exercise, progressive overload"
        elif "Level 4" in fitness_level or "Advanced" in fitness_level:
            base_rpe = "7-9 (Hard to Very Hard)"
            volume_guidance = "4-5 sets per exercise, periodized intensity"
        else:
            base_rpe = "5-7 (Moderate)"
            volume_guidance = "3 sets per exercise"
        
        # Medical condition adjustments
        medical_cap = ""
        if medical_conditions and medical_conditions != ["None"]:
            conditions_lower = [c.lower() for c in medical_conditions]
            if any(x in ' '.join(conditions_lower) for x in ['hypertension', 'cardiovascular', 'heart']):
                medical_cap = "\n**MEDICAL CAP: Maximum RPE 6-7 due to cardiovascular condition. NO maximal efforts.**"
            elif any(x in ' '.join(conditions_lower) for x in ['arthritis', 'joint', 'osteo']):
                medical_cap = "\n**MEDICAL CAP: Maximum RPE 7. Avoid high-impact. Pain-free range only.**"
            elif any(x in ' '.join(conditions_lower) for x in ['diabetes']):
                medical_cap = "\n**MEDICAL CAP: Maximum RPE 7-8. Monitor for signs of hypo/hyperglycemia.**"
        
        # Age adjustments
        age_guidance = ""
        if age >= 60:
            age_guidance = "\n**AGE ADJUSTMENT: Conservative intensity. Prioritize movement quality over load. Extended warm-up mandatory.**"
        elif age >= 50:
            age_guidance = "\n**AGE ADJUSTMENT: Moderate intensity focus. Joint-friendly exercises prioritized.**"
        
        return f"""
**9. INTENSITY & VOLUME PRECISION (STRICTLY ENFORCE):**

**Base Intensity for {fitness_level}:**
- RPE Range: {base_rpe}
- Volume: {volume_guidance}
- Progression: Increase reps/sets before increasing load{medical_cap}{age_guidance}

**RPE Scale Reference (Educate User):**
- RPE 1-2: Very light activity, minimal effort
- RPE 3-4: Light effort, comfortable, can maintain conversation easily
- RPE 5-6: Moderate effort, breathing harder but can still talk
- RPE 7-8: Hard effort, difficult to maintain conversation
- RPE 9-10: Maximum effort, cannot sustain for long

**Goal-Specific Intensity Adjustments:**
"""

    def _get_condition_guidelines(self, medical_conditions: List[str]) -> str:
        """Provide detailed medical condition guidelines"""
        if not medical_conditions or medical_conditions == ["None"]:
            return "No medical conditions reported. Standard exercise precautions apply."
        
        guidelines = []
        
        for condition in medical_conditions:
            condition_lower = condition.lower()
            
            if "hypertension" in condition_lower or "high blood pressure" in condition_lower:
                guidelines.append("""
**HYPERTENSION (High Blood Pressure):**
- ✓ SAFE: Moderate aerobic exercise, dynamic resistance training with breathing
- ✓ RECOMMENDED: 30-60 sec rest between sets, RPE 4-6 maximum
- ⚠ CAUTION: Avoid breath-holding (Valsalva maneuver), teach exhale on exertion
- ✗ AVOID: Maximal lifts, overhead pressing without proper breathing, isometric holds >10 sec
""")
            
            elif "diabetes" in condition_lower:
                guidelines.append("""
**DIABETES (Type 1 or Type 2):**
- ✓ SAFE: Moderate intensity resistance and aerobic training
- ✓ RECOMMENDED: Consistent exercise timing, have fast-acting carbs available
- ⚠ CAUTION: Monitor for hypoglycemia signs (shakiness, confusion, sweating)
- ✗ AVOID: Exercising if blood glucose <100 mg/dL or >250 mg/dL with ketones
""")
            
            elif "arthritis" in condition_lower or "osteoarthritis" in condition_lower:
                guidelines.append("""
**OSTEOARTHRITIS:**
- ✓ SAFE: Low-impact exercises, aquatic exercise, controlled ROM movements
- ✓ RECOMMENDED: Warm up thoroughly (7-10 min), move in pain-free range only
- ⚠ CAUTION: Some discomfort OK, but sharp pain = stop immediately
- ✗ AVOID: High-impact (jumping, running), heavy loaded end-range movements
""")
            
            elif "back pain" in condition_lower or "lower back" in condition_lower:
                guidelines.append("""
**CHRONIC BACK PAIN:**
- ✓ SAFE: Neutral spine exercises, core stabilization, hip mobility work
- ✓ RECOMMENDED: McGill Big 3 (curl-up, side plank, bird dog), gentle stretching
- ⚠ CAUTION: Maintain neutral spine during ALL exercises
- ✗ AVOID: Loaded spinal flexion (sit-ups with weight), ballistic twisting, heavy deadlifts without clearance
""")
            
            elif "knee" in condition_lower:
                guidelines.append("""
**KNEE ISSUES:**
- ✓ SAFE: Partial ROM exercises, terminal knee extension, hip strengthening
- ✓ RECOMMENDED: Quad and hip strengthening, avoid deep knee flexion initially
- ⚠ CAUTION: Pain-free range only, avoid knee valgus (knees caving in)
- ✗ AVOID: Deep squats/lunges (>90° initially), high-impact jumping, kneeling exercises
""")
            
            elif "shoulder" in condition_lower:
                guidelines.append("""
**SHOULDER ISSUES:**
- ✓ SAFE: Scapular stabilization, rotator cuff strengthening, controlled ROM
- ✓ RECOMMENDED: Band pull-aparts, YTWs, rows, gradually increase ROM
- ⚠ CAUTION: Avoid painful arc, maintain scapular control
- ✗ AVOID: Overhead pressing if painful, behind-neck movements, extreme ROM under load
""")
            
            elif "cardiovascular" in condition_lower or "heart" in condition_lower:
                guidelines.append("""
**CARDIOVASCULAR DISEASE:**
- ✓ SAFE: Moderate intensity aerobic, circuit resistance training with extended rest
- ✓ RECOMMENDED: Extended warm-up (10 min), RPE 3-5 maximum, monitor heart rate
- ⚠ CAUTION: Stop if chest pain, dizziness, unusual shortness of breath
- ✗ AVOID: High intensity intervals, maximal efforts, Valsalva maneuver
""")
            
            elif "osteoporosis" in condition_lower:
                guidelines.append("""
**OSTEOPOROSIS:**
- ✓ SAFE: Weight-bearing exercises, resistance training, balance work
- ✓ RECOMMENDED: Progressive resistance, impact within tolerance, fall prevention
- ⚠ CAUTION: Avoid spinal flexion, use proper lifting mechanics
- ✗ AVOID: Spinal flexion exercises (crunches), high-impact if severe, ballistic movements
""")
            
            elif "asthma" in condition_lower:
                guidelines.append("""
**ASTHMA:**
- ✓ SAFE: Interval training (work-rest), indoor exercise in cold weather
- ✓ RECOMMENDED: Inhaler accessible, thorough warm-up, controlled breathing
- ⚠ CAUTION: Stop if wheezing/difficulty breathing beyond normal exertion
- ✗ AVOID: Sustained high-intensity without breaks, exercising in cold/dry air if triggered
""")
            
            else:
                guidelines.append(f"""
**{condition.upper()}:**
- ⚠ GENERAL CAUTION: Conservative approach, pain-free movement only
- ✓ RECOMMENDED: Consult healthcare provider for specific clearances
- Monitor for any adverse symptoms during exercise
""")
        
        return "\n".join(guidelines)
    
    def _get_age_adaptations(self, age: int, medical_conditions: List[str]) -> str:
        """Provide age-specific adaptations and considerations"""
        
        if age < 30:
            return """
**4. AGE-SPECIFIC ADAPTATIONS (YOUNG ADULT: 18-29):**

**Training Advantages:**
- High recovery capacity (can train more frequently)
- Good movement learning capability
- Fewer restrictions on exercise selection

**Programming Notes:**
- Progressive overload: Can advance quickly with proper technique
- Variety: Use diverse training modalities to build broad fitness base
- Injury prevention: Emphasize movement quality even though you can "get away" with poor form
- Long-term focus: Build habits and patterns that sustain lifelong fitness
"""
        
        elif age < 50:
            return """
**4. AGE-SPECIFIC ADAPTATIONS (ADULT: 30-49):**

**Training Considerations:**
- Recovery: May need 48-72 hours between intense sessions for same muscle groups
- Joint health: Prioritize joint-friendly exercise variations
- Mobility: Include dedicated mobility work (5-10 min daily)
- Realistic expectations: Progress may be slower than in 20s but still very achievable

**Programming Notes:**
- Warm-up: Minimum 5-7 minutes, include dynamic mobility
- Exercise selection: Balance intensity with joint preservation
- Recovery: Adequate sleep (7-9 hours) and nutrition critical
- Variety: Mix high, moderate, and low intensity days
"""
        
        elif age < 65:
            return """
**4. AGE-SPECIFIC ADAPTATIONS (MATURE ADULT: 50-64):**

**Training Priorities:**
- Muscle preservation: Resistance training 2-3x/week minimum (sarcopenia prevention)
- Bone health: Weight-bearing and resistance exercises for bone density
- Balance: Include balance challenges in every session (fall prevention)
- Joint protection: Prefer low-impact, controlled movements

**Programming Notes:**
- Warm-up: Extended (7-10 minutes), emphasize joint mobility
- Intensity: Conservative RPE approach, quality over quantity
- Recovery: 48-72 hours between intense sessions mandatory
- Exercise selection: Favor bilateral support, avoid high-impact unless cleared
- Progression: Very gradual, focus on consistency over intensity

**MANDATORY SAFETY:**
- Balance work: Single-leg exercises, tandem stance, stability challenges
- Fall prevention: Never compromise balance for intensity
- Medical screening: Clearance recommended if starting new program
"""
        
        else:  # 65+
            return """
**4. AGE-SPECIFIC ADAPTATIONS (SENIOR: 65+):**

**CRITICAL SAFETY PRIORITIES:**
- Fall prevention: #1 concern - balance and stability in EVERY session
- Functional fitness: Prioritize activities of daily living (ADLs)
- Bone health: Gentle weight-bearing to maintain bone density
- Cognitive engagement: Exercise shown to support cognitive function

**Programming Notes:**
- Warm-up: Extended (10+ minutes), very gradual intensity increase
- Intensity: Conservative (RPE 3-6), never sacrifice form for load
- Recovery: 48-96 hours between sessions targeting same muscle groups
- Exercise selection: 
  * PRIORITIZE: Chair-supported exercises, wall-supported movements
  * INCLUDE: Balance work (near wall/support), functional patterns
  * AVOID: Plyometrics, ballistic movements, exercises requiring quick reactions

**MANDATORY BALANCE WORK:**
- Every session includes 5-10 min balance training
- Exercises near wall/chair for safety
- Progress: Two-leg → tandem stance → single-leg (near support)

**MEDICAL CONSIDERATIONS:**
- Likely multiple chronic conditions - conservative approach
- Medication interactions: Some medications affect exercise response
- Communication: Clear cues, avoid complex movement patterns
- Social aspect: Group exercise often beneficial for adherence

**EXERCISE MODIFICATIONS:**
- Squats → Chair sits/stands
- Push-ups → Wall push-ups
- Lunges → Step-ups (low height, supported)
- Planks → Wall planks or standing core exercises
- Floor work → Seated or standing alternatives (difficulty getting up/down)
"""
    
    def _get_fitness_level_rules(self, fitness_level: str) -> str:
        """Provide fitness level-specific programming rules with strict exercise constraints"""
    
        if "Level 1" in fitness_level or "Assisted" in fitness_level or "Low Function" in fitness_level:
            return """
**5. FITNESS LEVEL ADAPTATIONS (LEVEL 1 - ASSISTED / LOW FUNCTION):**

**CRITICAL PROFILE:** Needs support for balance, limited endurance, sedentary >6 months

**PRIMARY FOCUS:** Safety first, assisted movements only, build foundational movement capacity

**MANDATORY EXERCISE TYPES:**
- Chair-based exercises ONLY (chair squats, seated marches, chair push-ups)
- Wall-supported exercises (wall push-ups, wall slides, wall angels)
- Step taps (NO step-ups - too advanced)
- Light resistance bands (yellow/red bands only)
- Seated movements preferred

**STRICTLY PROHIBITED EXERCISES:**
- âœ— Floor exercises (getting up/down is too difficult)
- âœ— Planks, burpees, mountain climbers (too intense)
- âœ— Jumping or plyometrics of any kind
- âœ— Push-ups on floor (use wall or elevated surface)
- âœ— Lunges (balance risk - use chair squats instead)
- âœ— Any exercise requiring getting on hands/knees
- âœ— Free-standing balance work without support

**Programming Parameters:**
- Exercise complexity: SIMPLE, supported movements only
- Rep range: 6-10 reps (focus on quality, not quantity)
- Sets: 1-2 sets per exercise (build tolerance gradually)
- Rest: 90-120 seconds (full recovery essential)
- Tempo: VERY slow and controlled (4-0-4-0) - 4 seconds down, 4 seconds up
- RPE: 2-4 (very light - should feel "easy to manageable")
- Progression: Maintain same exercises for 4-6 weeks before advancing

**REQUIRED EXERCISE EXAMPLES:**
- Chair sits/stands (assisted with arms if needed)
- Seated leg lifts, seated marches
- Wall push-ups (start at arm's length from wall)
- Seated arm raises with no weight or very light bands
- Ankle circles, wrist circles (seated)
- Supported standing knee lifts (hold chair)

**SAFETY PROTOCOLS:**
- Chair MUST be sturdy and against wall
- All exercises near support (chair, wall, counter)
- Never compromise balance for movement
- Frequent rest breaks encouraged
- Expect session may take longer due to rest needs

**PSYCHOLOGICAL APPROACH:**
- Every small movement is progress
- Focus on consistency (2-3 days/week maximum)
- Celebrate completing exercises, not performance
- Build confidence in movement capability
"""
    
    elif "Level 2" in fitness_level or "Beginner Functional" in fitness_level:
        return """
**5. FITNESS LEVEL ADAPTATIONS (LEVEL 2 - BEGINNER FUNCTIONAL):**

**PROFILE:** Can perform light bodyweight tasks, mild conditions under control

**PRIMARY FOCUS:** Slow tempo bodyweight movements + mobility drills, build movement quality

**EXERCISE SELECTION GUIDELINES:**
- Bodyweight fundamental patterns (slow tempo emphasis)
- Mobility-focused movements (dynamic stretches, joint circles)
- Supported variations when needed (chair, wall)
- NO high-impact or complex movements yet

**ALLOWED EXERCISES:**
- âœ" Bodyweight squats (partial range OK)
- âœ" Wall/incline push-ups (NOT floor push-ups yet)
- âœ" Glute bridges (floor is OK at this level)
- âœ" Standing knee raises
- âœ" Step-ups (low height, 4-6 inches max)
- âœ" Light resistance band work
- âœ" Mobility drills (cat-cow, arm circles, hip circles)

**STILL PROHIBITED:**
- âœ— Floor push-ups (use incline)
- âœ— Lunges (use supported step-ups instead)
- âœ— Planks >20 seconds
- âœ— Jumping, burpees, mountain climbers
- âœ— Complex movement patterns

**Programming Parameters:**
- Exercise complexity: Simple fundamental patterns
- Rep range: 8-12 reps (building endurance)
- Sets: 2-3 sets per exercise
- Rest: 60-90 seconds
- Tempo: Slow and controlled (3-0-3-0)
- RPE: 3-5 (light to moderate - "I can do this")
- Progression: Increase reps, then sets, then difficulty over 4-6 weeks

**MOBILITY EMPHASIS:**
- Minimum 5 minutes mobility work in warm-up
- Include joint mobility every session
- Stretching and breathing in cool-down

**SAFETY NOTES:**
- Master form before adding any resistance
- Rest days mandatory (workout 3 days/week max)
- Some muscle soreness normal, sharp pain = stop
"""
    
    elif "Level 3" in fitness_level or "Moderate" in fitness_level or "Independent" in fitness_level:
        return """
**5. FITNESS LEVEL ADAPTATIONS (LEVEL 3 - MODERATE / INDEPENDENT):**

**PROFILE:** Can perform unassisted movements with mild fatigue

**PRIMARY FOCUS:** Build strength with resistance bands, light weights, low-impact cardio

**EXERCISE SELECTION GUIDELINES:**
- Unassisted bodyweight movements
- Resistance bands (all colors appropriate)
- Light dumbbells (2-10 lbs / 1-5 kg)
- Low-impact cardio options
- Bilateral before unilateral

**ALLOWED EXERCISES:**
- âœ" Full bodyweight squats, lunges (controlled)
- âœ" Floor push-ups (can modify to knees if needed)
- âœ" Planks (30-60 seconds)
- âœ" Glute bridges, single-leg bridges
- âœ" Dumbbell/band rows, presses
- âœ" Step-ups (8-12 inch height)
- âœ" Low-impact cardio (marching, step-touches, low-impact jacks)
- âœ" Dead bugs, bird dogs

**STILL PROHIBITED:**
- âœ— High-impact jumping (jump squats, burpees, box jumps)
- âœ— Heavy weights (keep it light-moderate)
- âœ— Complex Olympic lifts
- âœ— Plyometric exercises

**Programming Parameters:**
- Exercise complexity: Fundamental to intermediate
- Rep range: 10-15 reps (work capacity building)
- Sets: 3 sets per exercise
- Rest: 45-60 seconds
- Tempo: Controlled (2-0-2-0)
- RPE: 5-7 (moderate - challenging but sustainable)
- Progression: Add resistance gradually, increase reps before weight

**RESISTANCE INTRODUCTION:**
- Start with bands, progress to light dumbbells
- Focus on control over load
- Master movement before adding weight

**WORKOUT STRUCTURE:**
- Can handle 4 workouts per week
- Mix strength and cardio
- Include dedicated mobility work
"""
    
    elif "Level 4" in fitness_level or "Active Wellness" in fitness_level:
        return """
**5. FITNESS LEVEL ADAPTATIONS (LEVEL 4 - ACTIVE WELLNESS):**

**PROFILE:** No severe limitations, accustomed to regular activity

**PRIMARY FOCUS:** Moderate intensity strength + balance training, structured progression

**EXERCISE SELECTION GUIDELINES:**
- Full range of movements available
- Moderate weights appropriate
- Balance challenges included
- Can introduce low-level plyometrics (if medically cleared)

**ALLOWED EXERCISES:**
- âœ" All bodyweight exercises (squats, lunges, push-ups, pull-ups)
- âœ" Moderate weight training (10-25 lbs / 5-12 kg dumbbells)
- âœ" Single-leg exercises (single-leg deadlifts, pistol squat progressions)
- âœ" Advanced planks (side planks, plank variations)
- âœ" Moderate plyometrics (IF no contraindications: jump squats, box jumps)
- âœ" Kettlebell work, TRX exercises
- âœ" Balance challenges (single-leg work, stability exercises)

**PROGRAMMING PARAMETERS:**
- Exercise complexity: Intermediate to advanced
- Rep range: 8-15 reps (depends on goal)
- Sets: 3-4 sets per exercise
- Rest: 30-60 seconds (goal-dependent)
- Tempo: Moderate to explosive (2-0-1-0)
- RPE: 6-8 (moderate to hard)
- Progression: Structured periodization

**TRAINING STRATEGIES:**
- Can handle 4-5 workouts per week
- Split routines appropriate (upper/lower, push/pull)
- Supersets and circuits can be used
- Include power development if appropriate

**BALANCE INTEGRATION:**
- Mandatory single-leg work each session
- Unilateral exercises prioritized
- Stability challenges included
"""
    
    elif "Level 5" in fitness_level or "Adaptive Advanced" in fitness_level:
        return """
**5. FITNESS LEVEL ADAPTATIONS (LEVEL 5 - ADAPTIVE ADVANCED):**

**PROFILE:** Experienced user managing mild conditions

**PRIMARY FOCUS:** Structured strength split, low-impact cardio, yoga integration

**EXERCISE SELECTION GUIDELINES:**
- Advanced movement patterns
- Moderate to heavy loads (while respecting medical conditions)
- Complex exercises with proper progressions
- Sport-specific training if applicable

**ALLOWED EXERCISES:**
- âœ" Advanced strength training (heavy squats, deadlifts, presses)
- âœ" Olympic lift variations (if mobility allows)
- âœ" Advanced bodyweight (muscle-ups, handstands, levers)
- âœ" Controlled plyometrics (respecting joint health)
- âœ" Advanced yoga poses and flows
- âœ" Complex kettlebell work
- âœ" Sport-specific movements

**PROGRAMMING PARAMETERS:**
- Exercise complexity: Advanced, full spectrum
- Rep range: 5-20 reps (periodized by goal and phase)
- Sets: 4-6 sets per exercise
- Rest: Highly variable (20 seconds to 3 minutes depending on goal)
- Tempo: Includes explosive, pause reps, tempo work
- RPE: 7-9 (hard to very hard, controlled high intensity)
- Progression: Sophisticated periodization (linear, undulating, block)

**ADVANCED STRATEGIES:**
- 5-6 workouts per week
- Structured split routines (push/pull/legs or body part splits)
- Periodization with deload weeks every 4-6 weeks
- Advanced techniques (drop sets, rest-pause, clusters)
- Includes yoga/mobility 1-2x per week

**ADAPTIVE CONSIDERATIONS:**
- Even at advanced level, respect medical conditions
- Smart progression over aggressive progression
- Include recovery and mobility work
- Monitor for overtraining

**INJURY PREVENTION:**
- Proper warm-ups non-negotiable (10+ min)
- Cool-down and stretching essential
- Listen to body signals (modify if needed)
- Maintain exercise variety to prevent overuse
"""
    
    else:
        return """
**5. FITNESS LEVEL ADAPTATIONS (GENERAL):**
- Exercise selection: Match complexity to demonstrated capability
- Progressive overload: Gradual increases in difficulty over time
- Recovery: Adequate rest between sessions
- Form: Always prioritized over load or volume
"""
    
    def _determine_exercise_count(self, session_duration: str) -> int:
        """Determine appropriate number of main exercises based on session duration"""
        if "15-30" in session_duration or "short" in session_duration.lower():
            return 4  # Short session
        elif "30-45" in session_duration:
            return 6  # Standard session
        elif "45-60" in session_duration:
            return 7  # Long session
        elif "60+" in session_duration or "60-90" in session_duration:
            return 8  # Extended session
        else:
            return 6  # Default
    
    def generate_workout_plan(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        is_modification: bool = False,
        modification_request: str = "",
        original_plan_context: str = None,
        max_retries: int = 2
    ) -> Dict:
        """
        Generate a single day's workout plan with validation and retry logic
        
        Args:
            user_profile: User profile dictionary
            day_name: Name of the day (e.g., "Monday", "Day 1")
            day_index: Index of the day (0-6)
            is_modification: Whether this is a modification request
            modification_request: The modification request text
            original_plan_context: Original plan for context
            max_retries: Maximum number of retry attempts if validation fails
        
        Returns:
            Dictionary with plan, validation score, and metadata
        """
        attempt = 0
        best_plan = None
        best_score = 0
        
        while attempt <= max_retries:
            try:
                # Build the system prompt
                system_prompt = self._build_system_prompt(
                    user_profile=user_profile,
                    day_name=day_name,
                    day_index=day_index,
                    is_modification=is_modification,
                    modification_request=modification_request,
                    original_plan_context=original_plan_context
                )
                
                # Prepare API request
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                payload = {
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Generate the complete workout plan for {day_name}. Follow ALL instructions precisely."}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2500
                }
                
                # Make API call
                response = requests.post(
                    self.endpoint_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                
                # Extract plan
                result = response.json()
                plan_text = result['choices'][0]['message']['content'].strip()
                
                # Extract exercises and update tracker
                exercises = self._extract_exercises_from_plan(plan_text)
                
                # Validate plan
                validation_score = self._validate_plan(plan_text, user_profile, day_name)
                
                # Track best attempt
                if validation_score > best_score:
                    best_score = validation_score
                    best_plan = plan_text
                
                # If score meets threshold, accept and update tracker
                if validation_score >= 85:
                    self.weekly_exercises_used['warmup'].update(exercises['warmup'])
                    self.weekly_exercises_used['main'].update(exercises['main'])
                    self.weekly_exercises_used['cooldown'].update(exercises['cooldown'])
                    
                    return {
                        'success': True,
                        'plan': plan_text,
                        'validation_score': validation_score,
                        'attempt': attempt + 1,
                        'exercises_used': exercises
                    }
                
                attempt += 1
                
            except requests.exceptions.RequestException as e:
                return {
                    'success': False,
                    'error': f"API request failed: {str(e)}",
                    'plan': None
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Unexpected error: {str(e)}",
                    'plan': None
                }
        
        # If all retries failed, return best attempt
        if best_plan:
            # Update tracker with best plan's exercises
            exercises = self._extract_exercises_from_plan(best_plan)
            self.weekly_exercises_used['warmup'].update(exercises['warmup'])
            self.weekly_exercises_used['main'].update(exercises['main'])
            self.weekly_exercises_used['cooldown'].update(exercises['cooldown'])
            
            return {
                'success': True,
                'plan': best_plan,
                'validation_score': best_score,
                'attempt': max_retries + 1,
                'warning': f"Plan scored {best_score}% (below 85% target)",
                'exercises_used': exercises
            }
        
        # Complete failure - use fallback
        return self._generate_fallback_plan(user_profile, day_name)
    
    def _extract_exercises_from_plan(self, plan_text: str) -> Dict[str, Set[str]]:
        """
        Extract exercise names from plan text for tracking variety
        
        Args:
            plan_text: The generated workout plan text
        
        Returns:
            Dictionary with sets of exercise names by section
        """
        exercises = {
            'warmup': set(),
            'main': set(),
            'cooldown': set()
        }
        
        # Split plan into sections
        sections = plan_text.split('\n')
        current_section = None
        
        for line in sections:
            line_lower = line.lower().strip()
            
            # Detect section headers
            if 'warm-up' in line_lower or 'warm up' in line_lower:
                current_section = 'warmup'
                continue
            elif 'main workout' in line_lower:
                current_section = 'main'
                continue
            elif 'cool-down' in line_lower or 'cool down' in line_lower:
                current_section = 'cooldown'
                continue
            
            # Extract exercise names
            if current_section and line.strip():
                # Look for patterns like "1. Exercise Name" or "Exercise Name –"
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    # Main workout exercise
                    exercise_name = line.split('.', 1)[1].strip().split('–')[0].split('\n')[0].strip()
                    if exercise_name and len(exercise_name) > 2:
                        exercises[current_section].add(exercise_name.lower())
                elif '–' in line or '-' in line:
                    # Warm-up or cool-down exercise
                    # === CONTINUATION FROM _extract_exercises_from_plan ===

                    exercise_name = line.split('—')[0].split('-')[0].strip()
                    # Remove common prefixes and clean up
                    exercise_name = exercise_name.replace('*', '').replace('#', '').strip()
                    if exercise_name and len(exercise_name) > 2:
                        exercises[current_section].add(exercise_name.lower())
        
        return exercises
    
    def _validate_plan(self, plan_text: str, user_profile: Dict, day_name: str) -> float:
        """
        Validate generated plan and return accuracy score (0-100%)
        
        Validation criteria:
        - Structural completeness (30 points)
        - Medical safety (25 points)
        - Goal alignment (20 points)
        - Exercise variety (15 points)
        - Format compliance (10 points)
        
        Args:
            plan_text: The generated workout plan
            user_profile: User profile dictionary
            day_name: Name of the day
        
        Returns:
            Float score from 0-100
        """
        score = 0.0
        max_score = 100.0
        
        # === SECTION 1: STRUCTURAL COMPLETENESS (30 points) ===
        structure_score = 0.0
        
        # Check for day title (5 points)
        if day_name.lower() in plan_text.lower() and ('focus' in plan_text.lower() or '—' in plan_text):
            structure_score += 5
        
        # Check for warm-up section (8 points)
        if any(keyword in plan_text.lower() for keyword in ['warm-up', 'warm up', 'warmup']):
            structure_score += 8
        
        # Check for main workout section (10 points)
        if 'main workout' in plan_text.lower():
            structure_score += 10
        
        # Check for cool-down section (7 points)
        if any(keyword in plan_text.lower() for keyword in ['cool-down', 'cool down', 'cooldown']):
            structure_score += 7
        
        score += structure_score
        
        # === SECTION 2: MEDICAL SAFETY (25 points) ===
        safety_score = 25.0  # Start with full points, deduct for violations
        
        medical_conditions = user_profile.get('medical_conditions', ['None'])
        age = user_profile.get('age', 30)
        
        # Check for contraindicated exercises
        if medical_conditions and medical_conditions != ['None']:
            conditions_lower = ' '.join([c.lower() for c in medical_conditions])
            plan_lower = plan_text.lower()
            
            # Hypertension checks
            if 'hypertension' in conditions_lower or 'blood pressure' in conditions_lower:
                # Deduct points for risky exercises
                if 'maximal' in plan_lower or 'max effort' in plan_lower:
                    safety_score -= 10
                if 'hold breath' in plan_lower:
                    safety_score -= 8
            
            # Arthritis checks
            if 'arthritis' in conditions_lower:
                if any(term in plan_lower for term in ['high-impact', 'jumping', 'plyometric']):
                    safety_score -= 10
            
            # Back pain checks
            if 'back pain' in conditions_lower or 'lower back' in conditions_lower:
                if any(term in plan_lower for term in ['loaded flexion', 'heavy deadlift', 'sit-up']):
                    safety_score -= 12
            
            # Cardiovascular checks
            if 'cardiovascular' in conditions_lower or 'heart' in conditions_lower:
                if 'rpe 9' in plan_lower or 'rpe 10' in plan_lower:
                    safety_score -= 15
        
        # Age-related safety
        if age >= 65:
            if any(term in plan_text.lower() for term in ['plyometric', 'jump', 'explosive']):
                safety_score -= 8
        
        score += max(0, safety_score)
        
        # === SECTION 3: GOAL ALIGNMENT (20 points) ===
        goal_score = 0.0
        primary_goal = user_profile.get('primary_goal', 'General Fitness').lower()
        plan_lower = plan_text.lower()
        
        # Weight loss alignment
        if 'weight loss' in primary_goal:
            goal_keywords = ['circuit', 'metabolic', 'calorie', 'cardio', 'hiit', 'high knees', 'burpee', 'mountain climber']
            matches = sum(1 for keyword in goal_keywords if keyword in plan_lower)
            goal_score = min(20, matches * 3)
        
        # Muscle gain alignment
        elif 'muscle' in primary_goal or 'hypertrophy' in primary_goal:
            goal_keywords = ['sets × reps', '6-12 reps', 'hypertrophy', 'progressive', 'tempo', 'resistance']
            matches = sum(1 for keyword in goal_keywords if keyword in plan_lower)
            goal_score = min(20, matches * 3.5)
        
        # Strength alignment
        elif 'strength' in primary_goal:
            goal_keywords = ['compound', 'deadlift', 'squat', 'press', '4-8 reps', 'strength', 'progressive overload']
            matches = sum(1 for keyword in goal_keywords if keyword in plan_lower)
            goal_score = min(20, matches * 3)
        
        # Cardio alignment
        elif 'cardio' in primary_goal or 'endurance' in primary_goal:
            goal_keywords = ['cardio', 'endurance', 'heart rate', 'interval', 'continuous', 'aerobic']
            matches = sum(1 for keyword in goal_keywords if keyword in plan_lower)
            goal_score = min(20, matches * 3.5)
        
        # Flexibility alignment
        elif 'flexibility' in primary_goal or 'mobility' in primary_goal:
            goal_keywords = ['stretch', 'mobility', 'flexibility', 'range of motion', 'dynamic', 'yoga']
            matches = sum(1 for keyword in goal_keywords if keyword in plan_lower)
            goal_score = min(20, matches * 3)
        
        else:  # General fitness
            goal_keywords = ['strength', 'cardio', 'flexibility', 'balance', 'core']
            matches = sum(1 for keyword in goal_keywords if keyword in plan_lower)
            goal_score = min(20, matches * 4)
        
        score += goal_score
        
        # === SECTION 4: EXERCISE VARIETY (15 points) ===
        variety_score = 15.0
        
        # Extract exercises from current plan
        current_exercises = self._extract_exercises_from_plan(plan_text)
        all_current = set()
        for section_exercises in current_exercises.values():
            all_current.update(section_exercises)
        
        # Check for repetition from previous days
        all_used = set()
        for section_exercises in self.weekly_exercises_used.values():
            all_used.update(section_exercises)
        
        # Calculate overlap
        overlap = all_current.intersection(all_used)
        overlap_count = len(overlap)
        
        # Deduct points for repetition
        if overlap_count > 0:
            variety_score -= min(15, overlap_count * 3)
        
        score += max(0, variety_score)
        
        # === SECTION 5: FORMAT COMPLIANCE (10 points) ===
        format_score = 0.0
        
        # Check for markdown formatting (2 points)
        if '###' in plan_text or '**' in plan_text:
            format_score += 2
        
        # Check for exercise structure (4 points)
        if 'benefit:' in plan_lower and 'how to perform:' in plan_lower:
            format_score += 4
        
        # Check for sets/reps notation (2 points)
        if '×' in plan_text or 'x' in plan_text:
            format_score += 2
        
        # Check for RPE/intensity (2 points)
        if 'rpe' in plan_lower or 'intensity' in plan_lower:
            format_score += 2
        
        score += format_score
        
        # Return final score (0-100)
        return round(score, 2)
    
    def _generate_fallback_plan(self, user_profile: Dict, day_name: str) -> Dict:
        """
        Generate a safe, basic fallback plan if AI generation fails
        
        Args:
            user_profile: User profile dictionary
            day_name: Name of the day
        
        Returns:
            Dictionary with fallback plan
        """
        name = user_profile.get('name', 'User')
        primary_goal = user_profile.get('primary_goal', 'General Fitness')
        fitness_level = user_profile.get('fitness_level', 'Level 2')
        
        fallback_plan = f"""### {day_name} — Full Body Focus (Fallback Plan)

**Note:** This is a safe, general fitness plan generated as a fallback. For a more personalized plan, please try generating again.

**Warm-Up (5-7 minutes)**

- Arm Circles — Shoulder mobility — 10 forward, 10 backward — Keep shoulders relaxed
- Leg Swings — Hip mobility — 10 each direction — Hold support for balance
- Torso Twists — Spinal rotation — 15 total — Keep hips stable
- March in Place — General warm-up — 1 minute — Gradually increase pace

**Main Workout (Target: Full Body)**

1. Bodyweight Squats

**Benefit:** Builds lower body strength and supports {primary_goal}
**How to Perform:**
1. Stand with feet shoulder-width apart
2. Lower hips back and down as if sitting in a chair
3. Keep chest up and knees tracking over toes
4. Push through heels to return to standing

**Sets × Reps:** 3 × 12
**Intensity:** RPE 5-6
**Rest:** 60 seconds
**Safety Cue:** Keep knees aligned with toes, avoid letting them cave inward

2. Push-Ups (Modified if needed)

**Benefit:** Develops upper body pushing strength
**How to Perform:**
1. Start in plank position (or on knees for modification)
2. Lower chest toward ground with elbows at 45 degrees
3. Keep core engaged and body in straight line
4. Push back to starting position

**Sets × Reps:** 3 × 10
**Intensity:** RPE 5-7
**Rest:** 60 seconds
**Safety Cue:** Maintain neutral spine throughout movement

3. Glute Bridges

**Benefit:** Strengthens glutes and posterior chain
**How to Perform:**
1. Lie on back with knees bent, feet flat on floor
2. Drive through heels to lift hips toward ceiling
3. Squeeze glutes at top position
4. Lower with control

**Sets × Reps:** 3 × 15
**Intensity:** RPE 5-6
**Rest:** 45 seconds
**Safety Cue:** Avoid arching lower back excessively

4. Plank Hold

**Benefit:** Builds core stability and endurance
**How to Perform:**
1. Start in forearm plank position
2. Keep body in straight line from head to heels
3. Engage core and glutes
4. Hold for specified time

**Sets × Reps:** 3 × 30 seconds
**Intensity:** RPE 6-7
**Rest:** 60 seconds
**Safety Cue:** Don't let hips sag or pike up

5. Standing Knee Raises

**Benefit:** Improves balance and core engagement
**How to Perform:**
1. Stand tall with core engaged
2. Lift one knee toward chest
3. Lower with control and repeat other side
4. Alternate legs for specified reps

**Sets × Reps:** 3 × 20 (10 each leg)
**Intensity:** RPE 4-5
**Rest:** 45 seconds
**Safety Cue:** Keep standing leg stable, use wall if needed for balance

6. Bodyweight Rows (using sturdy table/bar)

**Benefit:** Develops upper body pulling strength
**How to Perform:**
1. Lie under sturdy table or bar at waist height
2. Grab edge with overhand grip
3. Pull chest toward edge, keeping body straight
4. Lower with control

**Sets × Reps:** 3 × 10
**Intensity:** RPE 6-7
**Rest:** 60 seconds
**Safety Cue:** Ensure table/bar is secure before starting

**Cool-Down (5-7 minutes)**

- Standing Hamstring Stretch — Hamstrings — 60 seconds each leg — Keep back straight
- Chest Doorway Stretch — Chest and shoulders — 60 seconds — Gentle pressure forward
- Child's Pose — Full body relaxation — 90 seconds — Focus on deep breathing
- Seated Spinal Twist — Lower back — 45 seconds each side — Rotate gently

**End of Workout**

Great work, {name}! Remember to stay hydrated and listen to your body.
"""
        
        return {
            'success': True,
            'plan': fallback_plan,
            'validation_score': 70,
            'is_fallback': True,
            'attempt': 1
        }
    
    def generate_full_program(
        self,
        user_profile: Dict,
        days_per_week: int = 5,
        week_number: int = 1
    ) -> Dict:
        """
        Generate a complete weekly workout program
        
        Args:
            user_profile: User profile dictionary
            days_per_week: Number of workout days (3-6 recommended)
            week_number: Week number for progression tracking
        
        Returns:
            Dictionary with complete program and metadata
        """
        # Reset weekly exercise tracker
        self.reset_weekly_tracker()
        
        # Define day names
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        selected_days = day_names[:days_per_week]
        
        # Initialize program structure
        program = {
            'success': True,
            'week_number': week_number,
            'days_per_week': days_per_week,
            'user_name': user_profile.get('name', 'User'),
            'primary_goal': user_profile.get('primary_goal', 'General Fitness'),
            'daily_plans': [],
            'overall_validation_score': 0.0,
            'generation_metadata': {
                'total_attempts': 0,
                'failed_days': [],
                'warnings': []
            }
        }
        
        total_score = 0.0
        successful_days = 0
        
        # Generate each day's plan
        for day_index, day_name in enumerate(selected_days):
            print(f"Generating {day_name}'s workout plan...")
            
            # Generate plan with retry logic
            result = self.generate_workout_plan(
                user_profile=user_profile,
                day_name=day_name,
                day_index=day_index,
                max_retries=2
            )
            
            # Track metadata
            program['generation_metadata']['total_attempts'] += result.get('attempt', 1)
            
            if result['success']:
                daily_plan = {
                    'day_name': day_name,
                    'day_index': day_index,
                    'plan_text': result['plan'],
                    'validation_score': result.get('validation_score', 0),
                    'attempts': result.get('attempt', 1),
                    'is_fallback': result.get('is_fallback', False)
                }
                
                program['daily_plans'].append(daily_plan)
                total_score += result.get('validation_score', 0)
                successful_days += 1
                
                # Track warnings
                if 'warning' in result:
                    program['generation_metadata']['warnings'].append(
                        f"{day_name}: {result['warning']}"
                    )
                
                print(f"✓ {day_name} completed (Score: {result.get('validation_score', 0)}%)")
            else:
                program['generation_metadata']['failed_days'].append(day_name)
                program['success'] = False
                print(f"✗ {day_name} generation failed: {result.get('error', 'Unknown error')}")
        
        # Calculate overall validation score
        if successful_days > 0:
            program['overall_validation_score'] = round(total_score / successful_days, 2)
        
        # Add program summary
        program['summary'] = self._generate_program_summary(program)
        
        return program
    
    def _generate_program_summary(self, program: Dict) -> str:
        """
        Generate a summary of the weekly program
        
        Args:
            program: Complete program dictionary
        
        Returns:
            Formatted summary string
        """
        user_name = program['user_name']
        week_number = program['week_number']
        days_per_week = program['days_per_week']
        overall_score = program['overall_validation_score']
        primary_goal = program['primary_goal']
        
        summary = f"""
# {user_name}'s Week {week_number} Fitness Program

**Program Overview:**
- Primary Goal: {primary_goal}
- Training Days: {days_per_week} days per week
- Overall Quality Score: {overall_score}%

**Weekly Schedule:**
"""
        
        for daily_plan in program['daily_plans']:
            day_name = daily_plan['day_name']
            score = daily_plan['validation_score']
            is_fallback = daily_plan.get('is_fallback', False)
            fallback_note = " (Fallback Plan)" if is_fallback else ""
            
            summary += f"- **{day_name}:** Quality Score {score}%{fallback_note}\n"
        
        # Add performance notes
        if program['overall_validation_score'] >= 90:
            summary += "\n**Performance:** Excellent! All workouts meet high-quality standards.\n"
        elif program['overall_validation_score'] >= 80:
            summary += "\n**Performance:** Very good. Most workouts meet quality standards.\n"
        elif program['overall_validation_score'] >= 70:
            summary += "\n**Performance:** Good. Workouts are safe and effective.\n"
        else:
            summary += "\n**Performance:** Basic plans generated. Consider regenerating for better quality.\n"
        
        # Add warnings if any
        if program['generation_metadata']['warnings']:
            summary += "\n**Notices:**\n"
            for warning in program['generation_metadata']['warnings']:
                summary += f"- {warning}\n"
        
        return summary
    
    def modify_workout_plan(
        self,
        user_profile: Dict,
        day_name: str,
        day_index: int,
        modification_request: str,
        original_plan: str
    ) -> Dict:
        """
        Modify an existing workout plan based on user feedback
        
        Args:
            user_profile: User profile dictionary
            day_name: Name of the day
            day_index: Index of the day
            modification_request: What to change
            original_plan: The original plan text
        
        Returns:
            Dictionary with modified plan
        """
        return self.generate_workout_plan(
            user_profile=user_profile,
            day_name=day_name,
            day_index=day_index,
            is_modification=True,
            modification_request=modification_request,
            original_plan_context=original_plan,
            max_retries=1
        )
    
    def get_exercise_library(self, equipment: List[str], body_part: str = "Full Body") -> List[str]:
        """
        Return a list of appropriate exercises based on equipment and body part
        
        Args:
            equipment: Available equipment list
            body_part: Target body part or "Full Body"
        
        Returns:
            List of exercise names
        """
        library = []
        
        # Base bodyweight exercises
        bodyweight_exercises = {
            "Full Body": [
                "Burpees", "Mountain Climbers", "Jump Squats", "Bear Crawls",
                "Inchworms", "Plank Jacks", "Jumping Jacks", "High Knees"
            ],
            "Upper Body": [
                "Push-ups", "Pike Push-ups", "Tricep Dips", "Diamond Push-ups",
                "Wide Push-ups", "Decline Push-ups", "Plank", "Side Plank"
            ],
            "Lower Body": [
                "Squats", "Lunges", "Glute Bridges", "Single-Leg Deadlifts",
                "Calf Raises", "Wall Sits", "Step-ups", "Bulgarian Split Squats"
            ],
            "Core": [
                "Planks", "Side Planks", "Dead Bugs", "Bird Dogs", "Bicycle Crunches",
                "Russian Twists", "Leg Raises", "Mountain Climbers", "Flutter Kicks"
            ]
        }
        
        # Add bodyweight exercises for target area
        if body_part in bodyweight_exercises:
            library.extend(bodyweight_exercises[body_part])
        else:
            library.extend(bodyweight_exercises["Full Body"])
        
        # Add equipment-specific exercises
        equipment_str = ' '.join(equipment).lower()
        
        if 'dumbbell' in equipment_str:
            if "Upper Body" in body_part or "Full Body" in body_part:
                library.extend([
                    "Dumbbell Bench Press", "Dumbbell Rows", "Shoulder Press",
                    "Lateral Raises", "Bicep Curls", "Tricep Extensions",
                    "Chest Flys", "Hammer Curls"
                ])
            if "Lower Body" in body_part or "Full Body" in body_part:
                library.extend([
                    "Goblet Squats", "Romanian Deadlifts", "Dumbbell Lunges",
                    "Single-Leg Deadlifts", "Dumbbell Step-ups"
                ])
        
        if 'resistance band' in equipment_str:
            library.extend([
                "Band Chest Press", "Band Rows", "Band Lateral Walks",
                "Band Face Pulls", "Band Pallof Press", "Band Bicep Curls"
            ])
        
        if 'barbell' in equipment_str or 'gym' in equipment_str:
            library.extend([
                "Barbell Squats", "Deadlifts", "Bench Press", "Overhead Press",
                "Barbell Rows", "Pull-ups", "Chin-ups"
            ])
        
        return list(set(library))  # Remove duplicates
    
    def export_program_to_markdown(self, program: Dict) -> str:
        """
        Export complete program to formatted markdown
        
        Args:
            program: Complete program dictionary from generate_full_program
        
        Returns:
            Formatted markdown string
        """
        markdown = f"# FriskaAI Fitness Program\n\n"
        markdown += program['summary']
        markdown += "\n\n---\n\n"
        
        # Add each day's plan
        for daily_plan in program['daily_plans']:
            markdown += f"\n{daily_plan['plan_text']}\n\n"
            markdown += "---\n\n"
        
        return markdown
    
    def get_weekly_variety_report(self) -> Dict:
        """
        Get a report of exercise variety across the week
        
        Returns:
            Dictionary with variety statistics
        """
        total_warmup = len(self.weekly_exercises_used['warmup'])
        total_main = len(self.weekly_exercises_used['main'])
        total_cooldown = len(self.weekly_exercises_used['cooldown'])
        total_unique = total_warmup + total_main + total_cooldown
        
        return {
            'total_unique_exercises': total_unique,
            'warmup_exercises': total_warmup,
            'main_exercises': total_main,
            'cooldown_exercises': total_cooldown,
            'warmup_list': sorted(list(self.weekly_exercises_used['warmup'])),
            'main_list': sorted(list(self.weekly_exercises_used['main'])),
            'cooldown_list': sorted(list(self.weekly_exercises_used['cooldown']))
        }


# === END OF FitnessAdvisor CLASS ===




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
    # Unit selection
                unit_system = st.radio("Measurement System *", ["Metric (kg, cm)", "Imperial (lbs, inches)"], horizontal=True)
                
                if unit_system == "Metric (kg, cm)":
                    weight_kg = st.number_input("Weight (kg) *", min_value=30.0, max_value=300.0, value=70.0, step=0.5)
                    height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0, value=170.0, step=0.5)
                else:  # Imperial
                    weight_lbs = st.number_input("Weight (lbs) *", min_value=66.0, max_value=660.0, value=154.0, step=1.0)
                    height_inches = st.number_input("Height (inches) *", min_value=39.0, max_value=98.0, value=67.0, step=0.5)
                    
                    # Convert to metric for internal use
                    weight_kg = weight_lbs * 0.453592
                    height_cm = height_inches * 2.54
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
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Generate workout plans
                    # Generate workout plans
                    with st.spinner("🔄 Generating your personalized fitness plan... This may take 30-60 seconds."):
                        try:
                            progress_bar = st.progress(0)
                            
                            for idx, day in enumerate(days_per_week):
                                progress = (idx + 1) / len(days_per_week)
                                progress_bar.progress(progress)
                                
                                result = advisor.generate_workout_plan(
                                    st.session_state.user_profile,
                                    day,
                                    idx
                                )
                                
                                # Store the complete result
                                st.session_state.workout_plans[day] = result
                            
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
        # Display workout plans
        st.markdown('<div class="section-header">📅 Your Weekly Workout Schedule</div>', unsafe_allow_html=True)

        for day in profile['days_per_week']:
            with st.expander(f"📋 {day} Workout Plan", expanded=False):
                if day in st.session_state.workout_plans:
                    plan_data = st.session_state.workout_plans[day]
                    
                    # Check if it's the result dictionary or just the plan text
                    if isinstance(plan_data, dict):
                        plan_text = plan_data.get('plan', '')
                        validation_score = plan_data.get('validation_score', 0)
                    else:
                        plan_text = plan_data
                    
                    # Display the workout plan with proper markdown rendering
                    st.markdown(plan_text)
                else:
                    st.warning(f"Plan for {day} not available. Please regenerate.")
        
        # Download button
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
                plan_data = st.session_state.workout_plans[day]
                # Extract plan text if it's a dictionary
                if isinstance(plan_data, dict):
                    plan_text = plan_data.get('plan', '')
                else:
                    plan_text = plan_data
                full_plan += f"\n{plan_text}\n\n---\n"

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