"use client";


import {
    motion,
    useMotionValue,
    useReducedMotion
} from "motion/react";
import {
    Activity,
    useCallback,
    useEffect,
    useRef
} from "react";
import {
    animate,
    type AnimationOptions,
    type AnimationPlaybackControls,
    delay,
    type DOMKeyframesDefinition
} from "motion";


interface KeyboardEffectProps {
    children?: string;
    onComplete?: () => unknown;
    showStartCursor?: boolean;
    showEndCursor?: boolean;
}


export default function KeyboardEffect({ children: text = "", onComplete: onAnimationComplete, showStartCursor = true, showEndCursor = true }: KeyboardEffectProps) {


    // Set typing speed based on text length
    const typingSpeed = Math.pow(Math.max(text.length, 1), -0.15);

    // Get prefers reduced motion
    const prefersReducedMotion = useReducedMotion();

    // Reference text being displayed
    const displayText = useMotionValue(prefersReducedMotion ? text : "");

    // Refs for animation
    const cursorAnimation = useRef<AnimationPlaybackControls | null>(null);
    const cursorRef = useRef<HTMLDivElement | null>(null);
    const textSchedule = useRef<VoidFunction | null>(null);

    // Define cursor animation
    const cursorAnimationKeyframes = {
        opacity: [1, 1, 0, 0],
    } satisfies DOMKeyframesDefinition;
    const cursorAnimationOptions = {
        duration: 0.4,
        ease: "linear",
        times: [0, 0.5, 0.5, 1],
        repeatType: "reverse"
    } satisfies AnimationOptions;

    // Hide the cursor
    const hideCursor = useCallback(() => {
        cursorAnimation.current = animate(
            cursorRef.current!,
            cursorAnimationKeyframes,
            {
                ...cursorAnimationOptions,
                repeat: 0
            }
        );
        cursorAnimation.current.finished.then(() => {
            cursorAnimation.current?.cancel();
        });
    }, [cursorAnimationKeyframes, cursorAnimationOptions]);

    // Start animating the cursor
    const startCursorAnimation = useCallback((onComplete?: VoidFunction, leaveOn: boolean = false) => {
        if(prefersReducedMotion) return;
        cursorAnimation.current = animate(
            cursorRef.current!,
            cursorAnimationKeyframes,
            {
                ...cursorAnimationOptions,
                repeat: leaveOn ? 5 : 6
            }
        );
        cursorAnimation.current.finished.then(() => {
            cursorAnimation.current?.cancel();
            onComplete?.();
        });
    }, [cursorAnimationKeyframes, cursorAnimationOptions, prefersReducedMotion]);

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
                    if(showEndCursor) {
                        startCursorAnimation(onAnimationComplete);
                    }
                    else {
                        hideCursor();
                        onAnimationComplete?.();
                    }
                }
                else {
                    queueNextText();
                }
            }, ((Math.random() * 0.2) + 0.05) * typingSpeed);

        };

        // If the text is not the target value, then begin scheduling keystrokes
        if(currentText !== text) {

            if(showStartCursor){
                startCursorAnimation(queueNextText, true);
            }
            else{
                queueNextText();
            }

        }

        return () => {
            textSchedule.current?.();
            textSchedule.current = null;
        }

    }, [displayText, hideCursor, onAnimationComplete, showEndCursor, showStartCursor, startCursorAnimation, text, typingSpeed]);


    // Render
    return (
        <motion.span className={"inline-block whitespace-nowrap text-current relative left-[1ex]"}>
            <motion.span className={"w-auto inline"}>{displayText}</motion.span>
            <Activity mode={prefersReducedMotion ? "hidden" : "visible"}>
                <motion.span ref={cursorRef} className={"inline-block h-[1em] w-[1ex] bg-current"} />
            </Activity>
        </motion.span>
    )

}
