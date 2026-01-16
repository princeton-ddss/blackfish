import { motion } from "framer-motion";
import { Typewriter } from "react-simple-typewriter";
import TaskButton from "./components/TaskButton";
import tasks from "./lib/tasks";

export default function DashboardPage() {
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <motion.h1
          className="text-2xl font-mono font-normal text-gray-800 mb-12"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Typewriter
            words={["What should we work on today?"]}
            loop={1}
            cursor
            cursorStyle="|"
            typeSpeed={60}
            deleteSpeed={50}
          />
        </motion.h1>

        <motion.div
          className="flex flex-col sm:flex-row justify-center gap-6"
          variants={container}
          initial="hidden"
          animate="show"
        >
          {tasks.map((task) => (
            <TaskButton key={task.id} task={task} icon={task.icon} />
          ))}
        </motion.div>
      </div>
    </div>
  );
}
