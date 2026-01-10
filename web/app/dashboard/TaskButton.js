"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { basePath } from "@/app/config";
import PropTypes from "prop-types";


function TaskButton({ task, icon: Icon }) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className="relative"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: isHovered ? 1 : 0, y: isHovered ? 0 : 10 }}
        className={"absolute top-14 -translate-x-1/2 w-full p-2 text-sm text-gray-800 font-light"}
      >
        {task.description}
      </motion.div>

      <motion.a
        href={`${basePath}/${task.path}`}
        className={
          "group relative flex items-center h-10 px-6 py-3 rounded-md border transition-all duration-100 text-gray-800 font-light space-x-2 hover:shadow-md hover:shadow-blue-100"
        }
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => setIsHovered(false)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <motion.div
          animate={{ rotate: isHovered ? 360 : 0 }}
          transition={{ duration: 0.5 }}
        >
          <Icon className="h-5 w-5" />
        </motion.div>
        <span className="font-normal">{task.name}</span>
      </motion.a>
    </motion.div>
  );
}

TaskButton.propTypes = {
  task: PropTypes.string,
  icon: PropTypes.node,
};

export default TaskButton;
