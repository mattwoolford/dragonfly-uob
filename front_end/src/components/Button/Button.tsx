import {
    type HTMLMotionProps,
    motion
}                             from "motion/react";
import type { CSSProperties } from "react";


interface ButtonProps extends HTMLMotionProps<'button'> {
    theme?: CSSProperties['color'];
    textHighlight?: "light" | "dark";
}


export default function Button({disabled, theme = "var(--color-text)", textHighlight = "light", style, ...props}: ButtonProps) {

    return (
        <motion.button className={"Button"}
                       initial={{
                           backgroundColor: "transparent",
                           color: disabled ? "var(--color-disabled)" : theme
                       }}
                       animate={{
                           backgroundColor: "transparent",
                           color: disabled ? "var(--color-disabled)" : theme
                       }}
                       whileHover={ disabled ? {} : {
                            color: textHighlight === "light" ? "var(--color-white)" : "var(--color-black)",
                            backgroundColor: theme,
                            scale: 0.97
                        }}
                        style={{
                            borderColor: disabled ? "var(--color-disabled)" : theme,
                            color: disabled ? "var(--color-disabled)" : theme,
                            ...style
                        }}
                        disabled={disabled}
                        {...props}
        />
    )

}
