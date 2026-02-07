import React, { useState, useEffect } from 'react';

export enum ScaffoldingLevel {
    Beginner = 'beginner',
    Intermediate = 'intermediate',
    Expert = 'expert'
}

interface LearnerProfile {
    user_id: string;
    skills: {
        verification?: number;
        intent_expression?: number;
        debugging?: number;
        architectural_reasoning?: number;
    };
}

interface Props {
    children: (level: ScaffoldingLevel, skills: LearnerProfile['skills']) => React.ReactNode;
    userId?: string;
}

const AdaptiveScaffolding: React.FC<Props> = ({ children, userId = "default_user" }) => {
    const [level, setLevel] = useState<ScaffoldingLevel>(ScaffoldingLevel.Beginner);
    const [skills, setSkills] = useState<LearnerProfile['skills']>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                // In a real app, use a proper API client
                const res = await fetch(`http://localhost:8002/learner/profile/${userId}`);
                if (res.ok) {
                    const data = await res.json();
                    const s = data.skills || {};
                    setSkills(s);

                    // Determine Level
                    const verificationSkill = s.verification || 0;
                    const intentSkill = s.intent_expression || 0;

                    if (verificationSkill > 5 && intentSkill > 5) {
                        setLevel(ScaffoldingLevel.Expert);
                    } else if (verificationSkill > 2 || intentSkill > 2) {
                        setLevel(ScaffoldingLevel.Intermediate);
                    } else {
                        setLevel(ScaffoldingLevel.Beginner);
                    }
                }
            } catch (e) {
                console.error("Failed to fetch learner profile", e);
            } finally {
                setLoading(false);
            }
        };

        fetchProfile();
    }, [userId]);

    return <>{children(level, skills)}</>;
};

export default AdaptiveScaffolding;
