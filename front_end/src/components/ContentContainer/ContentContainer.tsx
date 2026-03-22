import {
    type HTMLMotionProps,
    motion
}           from "motion/react";
import clsx from "clsx";


export default function ContentContainer({ children, layout: _layout, className, ...props }: HTMLMotionProps<"article">) {

    const cx = clsx("ContentContainer", className);

    return (
        <motion.article className={cx} layout {...props}>
            {children}
        </motion.article>
    )

}
