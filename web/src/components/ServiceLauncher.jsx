import React from "react";
import ServiceModal from "@/components/ServiceModal";
import { useModels } from "@/lib/loaders";
import PropTypes from "prop-types";

/**
 * Service Launcher component.
 * @param {object} options
 * @param {object} options.profile
 * @param {string} options.task
 * @param {object} options.defaultContainerOptions
 * @param {JSX.Element} options.ContainerOptionsFormComponent
 * @return {JSX.Element}
 */
function ServiceLauncher({
  profile,
  task,
  defaultContainerOptions,
  ContainerOptionsFormComponent
}) {
  const { models, isLoading } = useModels(profile, task)
  const [open, setOpen] = React.useState(false);
  const [launchSuccess, setLaunchSuccess] = React.useState(false);
  const [isLaunching, setIsLaunching] = React.useState(false);
  const [launchError, setLaunchError] = React.useState(null);
  const [containerOptions, setContainerOptions] = React.useState({
    ...defaultContainerOptions,
  });
  const [validationErrors, setValidationErrors] = React.useState({});

  return (
    <>
      <div className="pb-4 mb-4 border-b">
        <button
          type="button"
          className="mt-1 w-full flex flex-row justify-center gap-x-2 rounded-md bg-tranparent px-3.5 py-1.5 text-sm font-regular shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 border bg-blue-500 text-white disabled:bg-gray-50 disabled:text-gray-400 disabled:animate-pulse"
          onClick={() => {
            setOpen(true);
          }}
          disabled={!profile || (!models && isLoading)}
        >
          Open Launcher
        </button>
      </div>

      <ServiceModal
        task={task}
        open={open}
        setOpen={setOpen}
        defaultContainerOptions={defaultContainerOptions}
        containerOptions={containerOptions}
        setContainerOptions={setContainerOptions}
        launchSuccess={launchSuccess}
        setLaunchSuccess={setLaunchSuccess}
        isLaunching={isLaunching}
        setIsLaunching={setIsLaunching}
        launchError={launchError}
        setLaunchError={setLaunchError}
        validationErrors={validationErrors}
        setValidationErrors={setValidationErrors}
        profile={profile}
      >
        <ContainerOptionsFormComponent
          containerOptions={containerOptions}
          setContainerOptions={setContainerOptions}
          setValidationErrors={setValidationErrors}
          disabled={isLaunching || launchSuccess}
        />
      </ServiceModal>
    </>
  );
}

ServiceLauncher.propTypes = {
  profile: PropTypes.object,
  task: PropTypes.string,
  defaultContainerOptions: PropTypes.object,
  ContainerOptionsFormComponent: PropTypes.node,
};

export default ServiceLauncher;
