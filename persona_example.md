```json
{
  "dimensions": {
    "policy_stance_ages_5_10": [
      "Ban (K-5)",
      "Delay until grade 3",
      "Guided limited (K-5)",
      "Integrate across subjects (K-12)",
      "Opt-in / accommodation-based"
    ],
    "primary_rationale": [
      "Core skills (reading, writing, number sense, memory)",
      "Workflow readiness (modern tools, prompting, verification)",
      "Equity & access (closing resource gaps)",
      "Privacy & safety (data, surveillance, manipulation)",
      "Well-being & attention (motivation, self-regulation, social)"
    ],
    "trust_in_institutions_to_govern_ai": [
      "Low",
      "Mixed",
      "High"
    ],
    "school_environment_reference_point": [
      "Under-resourced urban public school",
      "Suburban public school",
      "Rural public school",
      "Private/charter school",
      "Homeschooling/unschooling"
    ],
    "personal_ai_exposure": [
      "Minimal/occasional user",
      "Workplace power-user",
      "School implementer/pilot participant",
      "Assistive-tech reliant user",
      "Policy/legal oversight role"
    ],
    "learner_lens_in_early_years": [
      "Foundational literacy (handwriting, reading stamina, writing)",
      "Foundational numeracy (number sense, mental math, reasoning)",
      "Language learning (ELL/bilingual support)",
      "Neurodiversity/attention (ADHD, autism, executive function)",
      "Disability/accessibility (dyslexia, vision/hearing, mobility)"
    ]
  },
  "personas": [
    {
      "name": "Maria Alvarez, 38",
      "type": "Delay-until-core-writing-returns",
      "dimensions": {
        "policy_stance_ages_5_10": "Delay until grade 3",
        "primary_rationale": "Core skills (reading, writing, number sense, memory)",
        "trust_in_institutions_to_govern_ai": "Mixed",
        "school_environment_reference_point": "Under-resourced urban public school",
        "personal_ai_exposure": "School implementer/pilot participant",
        "learner_lens_in_early_years": "Foundational literacy (handwriting, reading stamina, writing)"
      },
      "life_experience": "Maria teaches 2nd grade and watched her class go from proudly sounding out sentences to freezing when the district rolled out an \"AI writing helper\" during a short pilot. One student who used to fill a page with messy stories started turning in polished paragraphs he couldn’t read back aloud, and parent conferences turned into tearful conversations about confidence. She now leans toward delaying AI until kids can reliably write, revise, and explain their own thinking."
    },
    {
      "name": "Dev Patel, 41",
      "type": "Early-integration-with-verification-skills",
      "dimensions": {
        "policy_stance_ages_5_10": "Integrate across subjects (K-12)",
        "primary_rationale": "Workflow readiness (modern tools, prompting, verification)",
        "trust_in_institutions_to_govern_ai": "High",
        "school_environment_reference_point": "Suburban public school",
        "personal_ai_exposure": "Workplace power-user",
        "learner_lens_in_early_years": "Foundational numeracy (number sense, mental math, reasoning)"
      },
      "life_experience": "Dev manages a software team where junior hires who can’t sanity-check AI outputs ship bugs faster than ever, and he’s seen the cost of \"looks right\" thinking. At home, his 7-year-old likes asking an AI why math shortcuts work, and Dev turns it into a routine: estimate first, then verify. He leans strongly toward early integration paired with explicit habits of checking sources, testing answers, and explaining reasoning."
    },
    {
      "name": "Ruth McKenna, 57",
      "type": "Equity-first-guided-access",
      "dimensions": {
        "policy_stance_ages_5_10": "Guided limited (K-5)",
        "primary_rationale": "Equity & access (closing resource gaps)",
        "trust_in_institutions_to_govern_ai": "Mixed",
        "school_environment_reference_point": "Rural public school",
        "personal_ai_exposure": "Minimal/occasional user",
        "learner_lens_in_early_years": "Foundational literacy (handwriting, reading stamina, writing)"
      },
      "life_experience": "Ruth runs a small-town library where kids do homework in the only building with reliable Wi‑Fi, and she’s watched families drive 30 minutes just to print a worksheet. A grandmother she knows uses an AI voice feature to practice reading with her grandson because there’s no nearby tutor and the school’s intervention slots are full. Ruth worries about overuse, but she leans toward guided access because she’s seen how \"ban it\" often means only wealthier kids get it at home."
    },
    {
      "name": "Amina Hassan, 33",
      "type": "Language-support-integration",
      "dimensions": {
        "policy_stance_ages_5_10": "Guided limited (K-5)",
        "primary_rationale": "Equity & access (closing resource gaps)",
        "trust_in_institutions_to_govern_ai": "High",
        "school_environment_reference_point": "Suburban public school",
        "personal_ai_exposure": "Minimal/occasional user",
        "learner_lens_in_early_years": "Language learning (ELL/bilingual support)"
      },
      "life_experience": "Amina moved two years ago and still feels her stomach drop when school emails arrive full of idioms she doesn’t understand. She started using a translation/chat tool to rewrite teacher notes into simpler English and to practice bedtime conversations with her first-grader, who’s embarrassed to speak up in class. She leans toward early, supervised AI use because it’s been the first thing that made school feel navigable for their family."
    },
    {
      "name": "Jordan Lee, 29",
      "type": "Accommodation-based-access-advocate",
      "dimensions": {
        "policy_stance_ages_5_10": "Opt-in / accommodation-based",
        "primary_rationale": "Equity & access (closing resource gaps)",
        "trust_in_institutions_to_govern_ai": "Mixed",
        "school_environment_reference_point": "Suburban public school",
        "personal_ai_exposure": "Assistive-tech reliant user",
        "learner_lens_in_early_years": "Disability/accessibility (dyslexia, vision/hearing, mobility)"
      },
      "life_experience": "Jordan was diagnosed with dyslexia late and remembers being called \"lazy\" because reading aloud took so long that classmates finished whole chapters. In college, text-to-speech and smart summarizers were the first tools that let Jordan keep up without panic, and now Jordan mentors parents through IEP meetings. Jordan opposes blanket bans and argues for opt-in use framed as assistive support, with clear rules that separate accessibility from shortcutting."
    },
    {
      "name": "Elena Novak, 46",
      "type": "Privacy-first-delayer",
      "dimensions": {
        "policy_stance_ages_5_10": "Delay until grade 3",
        "primary_rationale": "Privacy & safety (data, surveillance, manipulation)",
        "trust_in_institutions_to_govern_ai": "Low",
        "school_environment_reference_point": "Private/charter school",
        "personal_ai_exposure": "Policy/legal oversight role",
        "learner_lens_in_early_years": "Foundational literacy (handwriting, reading stamina, writing)"
      },
      "life_experience": "Elena is a privacy attorney and once investigated a \"free\" classroom app that quietly collected location data and behavioral metrics tied to student IDs. When her child’s school announced an AI platform, she asked for the data-retention policy and got a vague one-page summary with no vendor audit. She leans toward delaying AI in early grades until enforceable safeguards exist, because she thinks the governance is lagging far behind the rollout."
    },
    {
      "name": "Marcus Johnson, 52",
      "type": "System-wide-integration-with-training",
      "dimensions": {
        "policy_stance_ages_5_10": "Integrate across subjects (K-12)",
        "primary_rationale": "Workflow readiness (modern tools, prompting, verification)",
        "trust_in_institutions_to_govern_ai": "High",
        "school_environment_reference_point": "Private/charter school",
        "personal_ai_exposure": "School implementer/pilot participant",
        "learner_lens_in_early_years": "Foundational numeracy (number sense, mental math, reasoning)"
      },
      "life_experience": "Marcus is a charter principal who spent a decade watching teachers burn out writing differentiated materials late at night, then leaving mid-year. After piloting an AI tool for lesson variants and parent communication (with strict on-device rules and no student accounts), he saw staff morale rebound and more time for small-group math. He leans toward integration because he believes the real risk is pretending these tools won’t exist and leaving kids untrained in how to use them responsibly."
    },
    {
      "name": "Sophie Chen, 35",
      "type": "Attention-and-motivation-guardrails",
      "dimensions": {
        "policy_stance_ages_5_10": "Guided limited (K-5)",
        "primary_rationale": "Well-being & attention (motivation, self-regulation, social)",
        "trust_in_institutions_to_govern_ai": "Mixed",
        "school_environment_reference_point": "Suburban public school",
        "personal_ai_exposure": "Minimal/occasional user",
        "learner_lens_in_early_years": "Neurodiversity/attention (ADHD, autism, executive function)"
      },
      "life_experience": "Sophie is a child psychologist and keeps seeing the same pattern: kids who already struggle with frustration tolerance gravitate to anything that removes the \"hard part\" of learning. One of her clients started refusing to draft stories unless an AI gave the first sentence, and the family’s nightly battles escalated. Sophie supports limited, teacher-guided AI use only when it’s clearly building self-regulation and reflection rather than replacing it."
    },
    {
      "name": "Caleb Turner, 44",
      "type": "Homeschool-core-strength-traditionalist",
      "dimensions": {
        "policy_stance_ages_5_10": "Ban (K-5)",
        "primary_rationale": "Core skills (reading, writing, number sense, memory)",
        "trust_in_institutions_to_govern_ai": "Low",
        "school_environment_reference_point": "Homeschooling/unschooling",
        "personal_ai_exposure": "Minimal/occasional user",
        "learner_lens_in_early_years": "Foundational literacy (handwriting, reading stamina, writing)"
      },
      "life_experience": "Caleb pulled his kids from school after pandemic-era remote lessons left his oldest anxious and constantly clicking between tabs instead of finishing anything. In their homeschool routine, he watches how long it took for handwriting practice to turn into independent journaling, and he doesn’t want a tool that can \"perform\" the work for them. He leans toward a K–5 ban because he sees early learning as training persistence and focus, not output quality."
    },
    {
      "name": "Teresa Gómez, 62",
      "type": "Basics-first-then-tools",
      "dimensions": {
        "policy_stance_ages_5_10": "Delay until grade 3",
        "primary_rationale": "Core skills (reading, writing, number sense, memory)",
        "trust_in_institutions_to_govern_ai": "Mixed",
        "school_environment_reference_point": "Under-resourced urban public school",
        "personal_ai_exposure": "Minimal/occasional user",
        "learner_lens_in_early_years": "Foundational numeracy (number sense, mental math, reasoning)"
      },
      "life_experience": "Teresa retired from bookkeeping and now volunteers twice a week helping kids with math at a community center. She’s had third-graders who can tap answers into a tablet but can’t tell her whether $19$ is closer to $20$ or $10$, which scares her more than low test scores. Teresa supports introducing AI later, after students can estimate, check, and explain—because she’s seen how tools can hide shaky number sense until it’s too late."
    }
  ]
}
```