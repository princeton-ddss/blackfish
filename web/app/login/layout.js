import { Suspense } from "react";
import PropTypes from "prop-types";

function LoginLayout({children}) {
  return (
    <Suspense>
      {children}
    </Suspense>
  );
}

LoginLayout.propTypes = {
  children: PropTypes.node,
};

export default LoginLayout;
