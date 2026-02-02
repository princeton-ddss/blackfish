import React from "react";
import { RocketLaunchIcon } from "@heroicons/react/24/outline";
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
      <button
        type="button"
        className="p-1.5 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700 disabled:text-gray-300 dark:disabled:text-gray-600 disabled:hover:bg-transparent"
        onClick={() => {
          setOpen(true);
        }}
        disabled={!profile || (!models && isLoading)}
        aria-label="Launch service"
      >
        <RocketLaunchIcon className="h-5 w-5" />
      </button>

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
  ContainerOptionsFormComponent: PropTypes.elementType,
};

export default ServiceLauncher;
