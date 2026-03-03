import type { RouteObject } from "react-router";
import Mission              from "./routes/mission/mission.tsx";
import ErrorBoundary        from "@routes/ErrorBoundary.tsx";


export default [{
    path: "/",
    element: <Mission />,
    ErrorBoundary
}] satisfies RouteObject[];
