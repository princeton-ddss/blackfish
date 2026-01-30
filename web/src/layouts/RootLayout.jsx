import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Dialog, DialogBackdrop, DialogPanel, TransitionChild } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { ProfileProvider } from "@/components/ProfileSelect";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import { ThemeProvider } from "@/providers/ThemeProvider";

function RootLayoutContent() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const pathname = location.pathname;
  const isLoginPage = pathname.endsWith("login");
  const isDashboard = pathname === "/dashboard" || pathname === "/";

  // Login page gets simple layout without sidebar
  if (isLoginPage) {
    return (
      <div className="font-sans">
        <Outlet />
      </div>
    );
  }

  // Dashboard gets simple layout without sidebar
  if (isDashboard) {
    return (
      <div className="font-sans min-h-screen bg-white dark:bg-gray-900 transition-colors">
        <Navbar variant="dashboard" />
        <section className="mb-4 mt-6 mx-8">
          <Outlet />
        </section>
      </div>
    );
  }

  return (
    <div className="font-sans min-h-screen bg-white dark:bg-gray-800 transition-colors">
      {/* Mobile sidebar drawer */}
      <Dialog open={sidebarOpen} onClose={setSidebarOpen} className="relative z-50 lg:hidden">
        <DialogBackdrop
          transition
          className="fixed inset-0 bg-gray-800/80 transition-opacity duration-300 ease-linear data-[closed]:opacity-0"
        />
        <div className="fixed inset-0 flex">
          <DialogPanel
            transition
            className="relative mr-16 flex w-full max-w-xs flex-1 transform transition duration-300 ease-in-out data-[closed]:-translate-x-full"
          >
            <TransitionChild>
              <div className="absolute top-0 left-full flex w-16 justify-center pt-5 duration-300 ease-in-out data-[closed]:opacity-0">
                <button type="button" onClick={() => setSidebarOpen(false)} className="-m-2.5 p-2.5">
                  <span className="sr-only">Close sidebar</span>
                  <XMarkIcon aria-hidden="true" className="h-6 w-6 text-white" />
                </button>
              </div>
            </TransitionChild>
            <Sidebar />
          </DialogPanel>
        </div>
      </Dialog>

      <Navbar showSidebar onOpenSidebar={() => setSidebarOpen(true)} />

      {/* Static sidebar for desktop - positioned below header */}
      <div className="hidden lg:fixed lg:top-12 lg:bottom-0 lg:left-0 lg:z-40 lg:flex lg:w-72 lg:flex-col">
        <Sidebar />
      </div>

      {/* Main content */}
      <main className="lg:pl-72">
        <div className="px-4 py-6 sm:px-6 lg:pl-8 lg:pr-2 lg:pt-16">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function RootLayout() {
  return (
    <ThemeProvider>
      <ProfileProvider>
        <RootLayoutContent />
      </ProfileProvider>
    </ThemeProvider>
  );
}

export default RootLayout;
