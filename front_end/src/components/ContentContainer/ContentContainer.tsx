import {
    type HTMLMotionProps,
    motion
}           from "motion/react";
import clsx from "clsx";


interface ContentContainerProps extends HTMLMotionProps<"article"> {
    maximise?: boolean;
}

export default function ContentContainer({
                                             children,
                                             className,
                                             maximise = false,
                                             style,
                                             ...props
                                         }: ContentContainerProps) {
    return (
        <motion.article
            className={clsx("ContentContainer", className)}
            layout
            style={{
                position: maximise ? "fixed" : "relative",
                inset: maximise ? 0 : undefined,
                width: maximise ? "100vw" : undefined,
                height: maximise ? "calc(100vh - (var(--spacing) * 20))" : undefined,
                marginTop: maximise ? "calc(var(--spacing) * 20)" : undefined,
                ...style,
            }}
            transition={{
                layout: {
                    type: "spring",
                    stiffness: 280,
                    damping: 30,
                    duration: 0.5
                },
            }}
            {...props}
        >
            {children}
        </motion.article>
    );
}
