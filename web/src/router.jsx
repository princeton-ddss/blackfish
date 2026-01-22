import { createBrowserRouter, Navigate } from "react-router-dom";
import { basePath } from "./config";

import RootLayout from "./layouts/RootLayout";
import DashboardPage from "./routes/dashboard/dashboard";
import LoginPage from "./routes/login/login";
import TextGenerationPage from "./routes/text-generation/text-generation";
import SpeechRecognitionPage from "./routes/speech-recognition/speech-recognition";
import FileManagerPage from "./routes/file-manager/file-manager";
import NotFoundPage from "./routes/not-found";

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <RootLayout />,
      children: [
        { index: true, element: <Navigate to="/dashboard" replace /> },
        { path: "dashboard", element: <DashboardPage /> },
        { path: "login", element: <LoginPage /> },
        { path: "text-generation", element: <TextGenerationPage /> },
        { path: "speech-recognition", element: <SpeechRecognitionPage /> },
        { path: "file-manager", element: <FileManagerPage /> },
        { path: "*", element: <NotFoundPage /> },
      ],
    },
  ],
  { basename: basePath || "/" },
);
