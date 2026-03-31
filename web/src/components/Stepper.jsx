import { CheckIcon } from "@heroicons/react/24/solid";
import PropTypes from "prop-types";

/**
 * A horizontal stepper component for multi-step forms.
 * @param {object} props
 * @param {Array} props.steps - Array of step objects with { id, name, description? }
 * @param {number} props.currentStep - Current step index (0-based)
 * @param {Function} props.isStepComplete - Function that returns true if step at index is complete
 * @param {Function} props.onStepClick - Optional callback when clicking a step
 */
function Stepper({ steps, currentStep, isStepComplete, onStepClick }) {
  const getStepStatus = (index) => {
    if (index === currentStep) return "current";
    if (isStepComplete && isStepComplete(index)) return "complete";
    return "upcoming";
  };

  return (
    <nav aria-label="Progress">
      <ol
        role="list"
        className="overflow-hidden rounded-md lg:flex lg:rounded-none"
      >
        {steps.map((step, stepIdx) => {
          const status = getStepStatus(stepIdx);
          const stepNumber = String(stepIdx + 1).padStart(2, "0");
          const isClickable = onStepClick && stepIdx !== currentStep;

          return (
            <li key={step.id} className="relative overflow-hidden lg:flex-1">
              <div
                className={`overflow-hidden border border-gray-200 dark:border-gray-600 lg:border-0 ${
                  stepIdx === 0 ? "rounded-t-md border-b-0" : ""
                } ${stepIdx === steps.length - 1 ? "rounded-b-md border-t-0" : ""}`}
              >
                {status === "complete" ? (
                  <button
                    type="button"
                    onClick={() => isClickable && onStepClick(stepIdx)}
                    className={`group w-full text-left ${isClickable ? "cursor-pointer" : "cursor-default"}`}
                  >
                    <span
                      aria-hidden="true"
                      className="absolute top-0 left-0 h-full w-1 bg-transparent group-hover:bg-gray-200 dark:group-hover:bg-gray-600 lg:top-auto lg:bottom-0 lg:h-1 lg:w-full"
                    />
                    <span
                      className={`flex items-start px-4 py-4 text-sm font-medium ${
                        stepIdx !== 0 ? "lg:pl-9" : ""
                      }`}
                    >
                      <span className="shrink-0">
                        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-500">
                          <CheckIcon aria-hidden="true" className="h-6 w-6 text-white" />
                        </span>
                      </span>
                      <span className="mt-0.5 ml-4 flex min-w-0 flex-col">
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {step.name}
                        </span>
                        {step.description && (
                          <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
                            {step.description}
                          </span>
                        )}
                      </span>
                    </span>
                  </button>
                ) : status === "current" ? (
                  <span aria-current="step">
                    <span
                      aria-hidden="true"
                      className="absolute top-0 left-0 h-full w-1 bg-blue-500 lg:top-auto lg:bottom-0 lg:h-1 lg:w-full"
                    />
                    <span
                      className={`flex items-start px-4 py-4 text-sm font-medium ${
                        stepIdx !== 0 ? "lg:pl-9" : ""
                      }`}
                    >
                      <span className="shrink-0">
                        <span className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-blue-500">
                          <span className="text-blue-500">{stepNumber}</span>
                        </span>
                      </span>
                      <span className="mt-0.5 ml-4 flex min-w-0 flex-col">
                        <span className="text-sm font-medium text-blue-500">
                          {step.name}
                        </span>
                        {step.description && (
                          <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
                            {step.description}
                          </span>
                        )}
                      </span>
                    </span>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => isClickable && onStepClick(stepIdx)}
                    className={`group w-full text-left ${isClickable ? "cursor-pointer" : "cursor-default"}`}
                  >
                    <span
                      aria-hidden="true"
                      className="absolute top-0 left-0 h-full w-1 bg-transparent group-hover:bg-gray-200 dark:group-hover:bg-gray-600 lg:top-auto lg:bottom-0 lg:h-1 lg:w-full"
                    />
                    <span
                      className={`flex items-start px-4 py-4 text-sm font-medium ${
                        stepIdx !== 0 ? "lg:pl-9" : ""
                      }`}
                    >
                      <span className="shrink-0">
                        <span className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-gray-300 dark:border-gray-600">
                          <span className="text-gray-500 dark:text-gray-400">{stepNumber}</span>
                        </span>
                      </span>
                      <span className="mt-0.5 ml-4 flex min-w-0 flex-col">
                        <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                          {step.name}
                        </span>
                        {step.description && (
                          <span className="text-sm font-normal text-gray-400 dark:text-gray-500">
                            {step.description}
                          </span>
                        )}
                      </span>
                    </span>
                  </button>
                )}

                {/* Chevron separator */}
                {stepIdx !== 0 && (
                  <div aria-hidden="true" className="absolute inset-0 top-0 left-0 hidden w-3 lg:block">
                    <svg
                      fill="none"
                      viewBox="0 0 12 82"
                      preserveAspectRatio="none"
                      className="h-full w-full text-gray-300 dark:text-gray-600"
                    >
                      <path
                        d="M0.5 0V31L10.5 41L0.5 51V82"
                        stroke="currentColor"
                        vectorEffect="non-scaling-stroke"
                      />
                    </svg>
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

Stepper.propTypes = {
  steps: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string,
    })
  ).isRequired,
  currentStep: PropTypes.number.isRequired,
  isStepComplete: PropTypes.func,
  onStepClick: PropTypes.func,
};

export default Stepper;
