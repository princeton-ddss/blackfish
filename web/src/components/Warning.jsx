import Alert from "@/components/Alert";
import PropTypes from "prop-types";

/**
 * Warning component.
 * @param {object} options
 * @param {string} options.header
 * @param {string} options.message
 * @return {JSX.Element}
 */
function Warning({ header, message }) {
  return (
    <Alert variant="warning" title={header} accent>
      {message}
    </Alert>
  );
}

Warning.propTypes = {
  header: PropTypes.string,
  message: PropTypes.string,
};

export default Warning;
