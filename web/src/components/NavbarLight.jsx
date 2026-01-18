import { Disclosure } from "@headlessui/react";
import { useState } from "react";
import { Dialog, DialogTitle, DialogPanel, Description } from "@headlessui/react";
import { LifebuoyIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { useLocation, Link } from "react-router-dom";
import { assetPath } from "@/config";
import PropTypes from "prop-types";

/**
 * Navbar Light component.
 * @param {object} options
 * @param {string} options.task
 * @return {JSX.Element}
 */
function NavbarLight({ task }) {
  const location = useLocation();
  const pathname = location.pathname;
  const isLoginPage = pathname.endsWith("login");

  const [isHelpModalOpen, setHelpModalOpen] = useState(false);

  const openHelpModal = () => setHelpModalOpen(true);
  const closeHelpModal = () => setHelpModalOpen(false);

  return (
    <Disclosure as="nav" className="bg-white">
      {() => (
        <>
          <div className="mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 justify-between">
              <div className="flex">
                <div className="flex flex-shrink-0 items-center">
                  <Link to="/dashboard">
                    <img
                      height="32"
                      width="32"
                      src={assetPath("/img/orca.png")}
                      alt="blackfish"
                    />
                  </Link>
                  <Link to="/dashboard">
                    <div className="pl-4 text-4xl text-gray-900 font-bold">blackfish</div>
                  </Link>
                  <div className="pl-4 text-4xl font-extralight text-slate-300 italic">
                    {task}
                  </div>
                </div>
              </div>

              {!isLoginPage && (
                <div className="flex items-center">
                  <button
                    onClick={openHelpModal}
                    className="text-black hover:text-blue-600 focus:outline-none transition-transform transform hover:scale-110"
                    aria-label="Help"
                  >
                    <LifebuoyIcon className="h-6 w-6" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {isHelpModalOpen && (
            <Dialog
              open={isHelpModalOpen}
              onClose={closeHelpModal}
              className="fixed inset-0 z-10 flex items-center justify-center p-4 bg-black bg-opacity-50"
            >
              <DialogPanel className="relative rounded-lg bg-white p-6 sm:max-w-lg shadow-md">
                <button
                  onClick={closeHelpModal}
                  className="absolute top-3 right-3 text-black hover:text-gray-700 focus:outline-none"
                  aria-label="Close"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
                <DialogTitle className="text-lg font-bold">
                  Having issues?
                </DialogTitle>
                <Description className="mt-2 text-sm text-gray-600">
                  Check out our issues page on GitHub. There, you can search for
                  known bugs, find solutions to common problems, or create a new
                  issue if nothing seems to meet your needs. Go ahead—drop us
                  a line!
                </Description>

                <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                  <a
                    type="button"
                    href="https://github.com/princeton-ddss/blackfish/issues"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center w-full justify-center rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 sm:col-start-2"
                  >
                    View on GitHub
                  </a>
                </div>
              </DialogPanel>
            </Dialog>
          )}
        </>
      )}
    </Disclosure>
  );
}

NavbarLight.propTypes = {
  task: PropTypes.string,
};

export default NavbarLight;
