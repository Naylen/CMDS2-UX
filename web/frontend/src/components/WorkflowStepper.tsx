/** Vertical stepper showing workflow completion status. */
import { Steps } from "antd";
import type { WorkflowStep } from "@/types";

interface Props {
  steps: WorkflowStep[];
  title?: string;
}

export default function WorkflowStepper({ steps, title }: Props) {
  // Find the current step (first incomplete)
  const current = steps.findIndex((s) => !s.done);
  const activeStep = current === -1 ? steps.length : current;

  return (
    <div>
      {title && (
        <div style={{ fontWeight: 600, marginBottom: 12 }}>{title}</div>
      )}
      <Steps
        direction="vertical"
        size="small"
        current={activeStep}
        items={steps.map((s) => ({
          title: s.label,
          status: s.done ? "finish" : undefined,
        }))}
      />
    </div>
  );
}
