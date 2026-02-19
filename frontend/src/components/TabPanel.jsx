import { useState } from 'react';

export default function TabPanel({ tabs, defaultTab = 0 }) {
    const [active, setActive] = useState(defaultTab);

    return (
        <div>
            <div className="tab-bar">
                {tabs.map((tab, i) => (
                    <button
                        key={i}
                        className={`tab-btn ${active === i ? 'active' : ''}`}
                        onClick={() => setActive(i)}
                    >
                        {tab.icon && <span>{tab.icon}</span>} {tab.label}
                    </button>
                ))}
            </div>
            <div className="tab-content">
                {tabs[active]?.content}
            </div>
        </div>
    );
}
