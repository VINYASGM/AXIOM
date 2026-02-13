import React, { useState, useEffect } from 'react';

interface ScrambleTextProps {
    text: string;
    className?: string;
    duration?: number;
}

const ScrambleText: React.FC<ScrambleTextProps> = ({ text, className, duration = 1 }) => {
    const [display, setDisplay] = useState(text);
    const chars = "!<>-_\\/[]{}—=+*^?#________";

    useEffect(() => {
        let iteration = 0;
        const interval = setInterval(() => {
            setDisplay(
                text.split("")
                    .map((char, index) => {
                        if (index < iteration) return text[index];
                        return chars[Math.floor(Math.random() * chars.length)];
                    })
                    .join("")
            );
            if (iteration >= text.length) clearInterval(interval);
            iteration += 1 / (duration * 20);
        }, 40);
        return () => clearInterval(interval);
    }, [text, duration]);

    return <span className={className}>{display}</span>;
};

export default ScrambleText;
