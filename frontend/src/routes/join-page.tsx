import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { CircleAlert, Loader2, LogIn } from "lucide-react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";

import { ApiError, joinCourse, type Student } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSession } from "@/session/session-context";

const joinSchema = z.object({
  courseCode: z.string().trim().min(1, "Enter your class code").max(64, "That code is too long"),
  displayName: z.string().trim().min(1, "Enter a display name").max(80, "That name is too long"),
});

type JoinForm = z.infer<typeof joinSchema>;

export function JoinPage() {
  const { session, startSession } = useSession();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<JoinForm>({
    resolver: zodResolver(joinSchema),
    defaultValues: { courseCode: "", displayName: "" },
  });

  const mutation = useMutation<Student, Error, JoinForm>({
    mutationFn: ({ courseCode, displayName }) => joinCourse(courseCode, displayName),
    onSuccess: (student) => {
      startSession({ courseId: student.course_id, student });
      navigate("/course");
    },
  });

  // Already joined → skip the form and go straight to the course.
  if (session) return <Navigate to="/course" replace />;

  const errorMessage =
    mutation.error instanceof ApiError && mutation.error.status === 404
      ? "That class doesn't exist yet — double-check the code with your instructor."
      : mutation.error
        ? "Couldn't join the class. Please try again."
        : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="mx-auto max-w-md"
    >
      <div className="mb-8 text-center">
        <h1 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">
          Join your class
        </h1>
        <p className="mt-3 text-pretty text-muted-foreground">
          Enter your class code to start asking questions and taking quizzes grounded in your course
          materials.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Class details</CardTitle>
          <CardDescription>Your instructor shares the class code.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            noValidate
            onSubmit={handleSubmit((values) => mutation.mutate(values))}
            className="space-y-4"
          >
            <div className="space-y-2">
              <Label htmlFor="courseCode">Class code</Label>
              <Input
                id="courseCode"
                placeholder="e.g. CS101"
                autoComplete="off"
                aria-invalid={errors.courseCode ? true : undefined}
                aria-describedby={errors.courseCode ? "courseCode-error" : undefined}
                {...register("courseCode")}
              />
              {errors.courseCode && (
                <p id="courseCode-error" role="alert" className="text-sm text-destructive">
                  {errors.courseCode.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="displayName">Display name</Label>
              <Input
                id="displayName"
                placeholder="e.g. Alex Kim"
                autoComplete="name"
                aria-invalid={errors.displayName ? true : undefined}
                aria-describedby={errors.displayName ? "displayName-error" : undefined}
                {...register("displayName")}
              />
              {errors.displayName && (
                <p id="displayName-error" role="alert" className="text-sm text-destructive">
                  {errors.displayName.message}
                </p>
              )}
            </div>

            {errorMessage && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
              >
                <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>{errorMessage}</span>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <>
                  <Loader2 className="animate-spin" aria-hidden="true" />
                  Joining…
                </>
              ) : (
                <>
                  <LogIn aria-hidden="true" />
                  Join class
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </motion.div>
  );
}
