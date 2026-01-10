import PropTypes from "prop-types";

function SpeechRecognitionLayout({ children }) {
  return <section className="mb-4 mt-6 ml-8 mr-8">{children}</section>;
}

SpeechRecognitionLayout.propTypes = {
  children: PropTypes.node,
};

export default SpeechRecognitionLayout;
