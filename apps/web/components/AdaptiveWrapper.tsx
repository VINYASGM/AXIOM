import React from 'react';
import { useLearnerStore, SkillDomain } from '../src/store/learnerStore';

interface AdaptiveWrapperProps {
    children: React.ReactNode;
    requiredSkill?: SkillDomain;
    minLevel?: number; // 0-10
    fallback?: React.ReactNode;
    featureName?: string; // For analytics/logging
}

/**
 * A wrapper component that shows/hides content based on user skill level.
 * Used to implement Progressive Disclosure.
 */
export const AdaptiveWrapper: React.FC<AdaptiveWrapperProps> = ({
    children,
    requiredSkill,
    minLevel = 1,
    fallback = null,
    featureName
}) => {
    const skills = useLearnerStore((state) => state.skills);
    const globalLevel = useLearnerStore((state) => state.globalLevel);

    // If no specific skill required, maybe check global level?
    // For now, if no skill required, just render.
    if (!requiredSkill) {
        return <>{children}</>;
    }

    const currentLevel = skills[requiredSkill] || 0;
    const hasSkill = currentLevel >= minLevel;

    // Debug/Admin override check could go here

    if (hasSkill) {
        return <>{children}</>;
    }

    return <>{fallback}</>;
};

/**
 * Higher-order component for simpler usage with default fallback
 */
export const withAdaptivity = (
    Component: React.ComponentType<any>,
    requiredSkill: SkillDomain,
    minLevel: number,
    FallbackComponent?: React.ComponentType<any>
) => {
    return (props: any) => (
        <AdaptiveWrapper
            requiredSkill={requiredSkill}
            minLevel={minLevel}
            fallback={FallbackComponent ? <FallbackComponent {...props} /> : null}
        >
            <Component {...props} />
        </AdaptiveWrapper>
    );
};
