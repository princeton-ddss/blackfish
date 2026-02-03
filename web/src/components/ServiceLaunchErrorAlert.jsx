import Alert from "@/components/Alert";
import PropTypes from "prop-types";

/**
 * Service Launch Error Alert component.
 * @param {object} options
 * @param {object} options.error
 * @param {string} options.error.message
 * @param {Function} options.onClick
 * @return {JSX.Element}
 */
function ServiceLaunchErrorAlert({ error, onClick }) {
  return (
    <Alert
      variant="error"
      title="Failed to launch service."
      onDismiss={onClick}
      className="mb-4"
    >
      <ul className="list-disc space-y-1 pl-5">
        <li>{error.message}</li>
      </ul>
    </Alert>
  );
}

ServiceLaunchErrorAlert.propTypes = {
  error: PropTypes.object,
  onClick: PropTypes.func,
};

export default ServiceLaunchErrorAlert;
