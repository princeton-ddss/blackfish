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
      <p>
        {error.message.split("\n").map((part, i) => (
          i === 0 ? <strong key={i}>{part} </strong> : part
        ))}
      </p>
    </Alert>
  );
}

ServiceLaunchErrorAlert.propTypes = {
  error: PropTypes.object,
  onClick: PropTypes.func,
};

export default ServiceLaunchErrorAlert;
