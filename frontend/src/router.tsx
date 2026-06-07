import { createBrowserRouter, type RouteObject } from "react-router-dom";

import { AppLayout } from "@/components/app-layout";
import { AskPage } from "@/routes/ask-page";
import { CourseHome } from "@/routes/course-home";
import { JoinPage } from "@/routes/join-page";
import { ProgressPage } from "@/routes/progress-page";
import { QuizPage } from "@/routes/quiz-page";
import { UploadPage } from "@/routes/upload-page";

export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <JoinPage /> },
      { path: "course", element: <CourseHome /> },
      { path: "upload", element: <UploadPage /> },
      { path: "ask", element: <AskPage /> },
      { path: "quiz", element: <QuizPage /> },
      { path: "progress", element: <ProgressPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
