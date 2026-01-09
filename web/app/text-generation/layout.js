import PropTypes from "prop-types";

function TextGenerateLayout({ children }) {
  return (
    <section className="mb-4 mt-6 ml-8 mr-8">
      {children}
    </section>
  );
}

TextGenerateLayout.propTypes = {
  children: PropTypes.node,
};

export default TextGenerateLayout;
