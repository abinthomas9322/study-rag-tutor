import { motion } from "framer-motion";
import { GraduationCap, MessagesSquare, ListChecks } from "lucide-react";

import { HealthBadge } from "@/components/health-badge";
import { ThemeToggle } from "@/components/theme-toggle";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: MessagesSquare,
    title: "Ask, grounded",
    description: "Answers cite the exact course material they came from — no hallucinations.",
  },
  {
    icon: ListChecks,
    title: "Practice quizzes",
    description: "Turn any topic into a multiple-choice quiz and get scored, explained feedback.",
  },
  {
    icon: GraduationCap,
    title: "One class, one space",
    description: "Upload materials once; the whole study group shares the same knowledge base.",
  },
] as const;

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <a href="/" className="flex items-center gap-2 font-semibold">
            <GraduationCap className="size-6 text-primary" aria-hidden="true" />
            <span>Study-Group RAG Tutor</span>
          </a>
          <div className="flex items-center gap-3">
            <HealthBadge />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="container flex-1 py-12">
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="mx-auto max-w-2xl text-center"
        >
          <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl">
            Study together, grounded in your own materials
          </h1>
          <p className="mt-4 text-pretty text-lg text-muted-foreground">
            Join your course, upload the readings once, then ask questions and generate quizzes —
            every answer cited from the source.
          </p>
        </motion.section>

        <section
          aria-labelledby="features-heading"
          className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-3"
        >
          <h2 id="features-heading" className="sr-only">
            What you can do
          </h2>
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="h-full">
              <CardHeader>
                <feature.icon className="size-6 text-primary" aria-hidden="true" />
                <CardTitle className="text-lg">{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
              <CardContent />
            </Card>
          ))}
        </section>
      </main>

      <footer className="border-t py-6">
        <div className="container text-center text-sm text-muted-foreground">
          Built for study groups · grounded answers, real citations
        </div>
      </footer>
    </div>
  );
}
