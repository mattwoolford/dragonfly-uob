import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import {
    createBrowserRouter,
    RouterProvider
}                     from "react-router";
import Routes         from "./routes";


const router = createBrowserRouter(Routes);

const root = document.getElementById('root');

createRoot(root!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
