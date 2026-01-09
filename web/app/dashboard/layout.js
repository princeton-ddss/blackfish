import PropTypes from "prop-types";

function DashboardLayout({ children }) {
  return (
    <section className="mb-4 mt-6 ml-8 mr-8">
      {children}
    </section>
  );
}

DashboardLayout.propTypes = {
  children: PropTypes.node,
};

export default DashboardLayout;
