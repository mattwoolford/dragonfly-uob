"use client";


import {
    motion,
    useMotionValue
} from "motion/react";
import {
    useEffect,
    useRef
} from "react";
import {
    animate,
    type AnimationPlaybackControls,
    delay
} from "motion";


interface KeyboardEffectProps {
    children?: string;
}


export default function KeyboardEffect({ children: text = "" }: KeyboardEffectProps) {

    const displayText = useMotionValue("");

    const cursorAnimation = useRef<AnimationPlaybackControls | null>(null);
    const cursorRef = useRef<HTMLDivElement | null>(null);
    const textSchedule = useRef<VoidFunction | null>(null);

    // Start animating the cursor
    const startCursorAnimation = (onComplete?: VoidFunction, leaveOn: boolean = false) => {
        cursorAnimation.current = animate(
            cursorRef.current!,
            {
                opacity: [1, 1, 0, 0],
            },
            {
                duration: 0.4,
                ease: "linear",
                times: [0, 0.5, 0.5, 1],
                repeat: leaveOn ? 5 : 6,
                repeatType: "reverse"
            }
        );
        cursorAnimation.current.finished.then(() => {
            cursorAnimation.current?.cancel();
            onComplete?.();
        });
    };

    // Queue letters to type when the text changes
    useEffect(() => {

        const currentText = displayText.get();

        // Get the next keyframe
        const getUpdatedText = (currentText: string, fullText: string): string => {
            if (!fullText.startsWith(currentText)) {
                return currentText;
            }

            if (currentText.length >= fullText.length) {
                return fullText;
            }

            return fullText.slice(0, currentText.length + 1);
        };

        // Recursively delay text updates (animate keystrokes)
        const queueNextText = () => {

            textSchedule.current = delay(() => {
                const updatedText = getUpdatedText(displayText.get(), text);
                displayText.set(updatedText);
                if (updatedText === text) {
                    startCursorAnimation();
                }
                else {
                    queueNextText();
                }
            }, (Math.random() * 0.2) + 0.05);

        };

        // If the text is not the target value, then begin scheduling keystrokes
        if(currentText !== text) {
            startCursorAnimation(queueNextText, true);
        }

        return () => {
            textSchedule.current?.();
            textSchedule.current = null;
        }

    }, [displayText, text]);


    // Render
    return (
        <motion.span className={"inline-block whitespace-nowrap text-white relative left-[1ex]"}>
            <motion.span className={"w-auto inline"}>{displayText}</motion.span>
            <motion.span ref={cursorRef} className={"inline-block h-[1em] w-[1ex] bg-current"} />
        </motion.span>
    )

}
