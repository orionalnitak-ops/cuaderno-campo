const ScreenCalendar = ({ user, campana }) => {
    const [events, setEvents] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [currentMonth, setCurrentMonth] = React.useState(new Date().getMonth());
    const [currentYear, setCurrentYear] = React.useState(new Date().getFullYear());
    const [selectedDate, setSelectedDate] = React.useState(new Date().toISOString().split('T')[0]);

    React.useEffect(() => {
        setLoading(true);
        fetch(`/api/calendario/eventos?year=${currentYear}&month=${currentMonth + 1}`)
            .then(r => r.json())
            .then(data => {
                setEvents(Array.isArray(data) ? data : []);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setEvents([]);
                setLoading(false);
            });
    }, [currentYear, currentMonth]);

    const daysInMonth = (month, year) => new Date(year, month + 1, 0).getDate();
    const firstDayOfMonth = (month, year) => {
        let day = new Date(year, month, 1).getDay();
        return day === 0 ? 6 : day - 1; // Adjust so Monday is 0
    };

    const nextMonth = () => {
        if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear(currentYear + 1); } 
        else { setCurrentMonth(currentMonth + 1); }
    };

    const prevMonth = () => {
        if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear(currentYear - 1); } 
        else { setCurrentMonth(currentMonth - 1); }
    };

    const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

    if (loading) return <div className="p-8 text-center animate-spin">⏳</div>;

    const daysCount = daysInMonth(currentMonth, currentYear);
    const startDay = firstDayOfMonth(currentMonth, currentYear);
    const calendarDays = [];

    // Fill empty days at start
    for (let i = 0; i < startDay; i++) {
        calendarDays.push(null);
    }
    // Fill actual days
    for (let i = 1; i <= daysCount; i++) {
        const dStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
        calendarDays.push(dStr);
    }

    const selectedEvents = events.filter(e => e.date === selectedDate);

    return (
        <div className="pb-32 bg-[#F7FAF8] min-h-screen">
            <div className="bg-[#1D9E75] text-white p-6 pt-12 shadow-sm rounded-b-3xl">
                <h1 className="text-2xl font-bold">Calendario</h1>
                <p className="text-emerald-100 text-sm">Vista de campaña: {campana}</p>
            </div>

            <div className="p-4">
                <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="flex justify-between items-center p-4 bg-emerald-50">
                        <button onClick={prevMonth} className="w-8 h-8 flex justify-center items-center rounded-full hover:bg-emerald-100 text-emerald-800 transition">
                            <i data-lucide="chevron-left" className="w-5 h-5"></i>
                        </button>
                        <h2 className="font-bold text-lg text-emerald-900">{monthNames[currentMonth]} {currentYear}</h2>
                        <button onClick={nextMonth} className="w-8 h-8 flex justify-center items-center rounded-full hover:bg-emerald-100 text-emerald-800 transition">
                            <i data-lucide="chevron-right" className="w-5 h-5"></i>
                        </button>
                    </div>

                    <div className="grid grid-cols-7 gap-px bg-gray-100">
                        {['L', 'M', 'X', 'J', 'V', 'S', 'D'].map(day => (
                            <div key={day} className="bg-white py-2 text-center text-xs font-bold text-gray-400">{day}</div>
                        ))}
                        {calendarDays.map((dateStr, index) => {
                            if (!dateStr) return <div key={`empty-${index}`} className="bg-gray-50 min-h-[60px]"></div>;
                            
                            const dayEvents = events.filter(e => e.date === dateStr);
                            const isSelected = selectedDate === dateStr;
                            const isToday = dateStr === new Date().toISOString().split('T')[0];
                            const dayNum = dateStr.split('-')[2].replace(/^0/, '');

                            return (
                                <div 
                                    key={dateStr} 
                                    onClick={() => setSelectedDate(dateStr)}
                                    className={`bg-white min-h-[60px] p-1 border-t-2 transition-colors cursor-pointer relative ${isSelected ? 'border-emerald-500 bg-emerald-50/30' : 'border-transparent hover:bg-gray-50'}`}
                                >
                                    <div className={`text-center text-sm font-medium w-6 h-6 mx-auto rounded-full flex items-center justify-center ${isToday ? 'bg-emerald-500 text-white' : 'text-gray-700'}`}>
                                        {dayNum}
                                    </div>
                                    <div className="flex flex-wrap justify-center gap-1 mt-1">
                                        {dayEvents.map((evt, i) => (
                                            <div key={i} className={`w-1.5 h-1.5 rounded-full ${evt.color}`}></div>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            <div className="px-4 mt-2">
                <h3 className="font-bold text-gray-800 mb-3 ml-2 flex items-center gap-2">
                    <i data-lucide="calendar" className="w-4 h-4 text-emerald-600"></i> Eventos del {selectedDate}
                </h3>
                
                {selectedEvents.length === 0 ? (
                    <div className="bg-white rounded-2xl p-6 text-center text-gray-400 border border-dash border-gray-200">
                        No hay eventos anotados.
                    </div>
                ) : (
                    <div className="space-y-3">
                        {selectedEvents.map((evt, i) => (
                            <div key={i} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 flex gap-3 items-center">
                                <div className={`w-2 stretch self-stretch rounded-full ${evt.color}`}></div>
                                <div>
                                    <p className="font-bold text-gray-900">{evt.title}</p>
                                    <p className="text-sm text-gray-500">{evt.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="px-6 mt-6 pb-6">
                 <div className="flex flex-wrap gap-3 text-xs font-medium text-gray-500 bg-white p-3 rounded-xl border border-gray-100">
                     <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span> Tratamientos</span>
                     <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block"></span> Riegos</span>
                     <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-400 inline-block"></span> Abonados</span>
                     <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block"></span> Alerta ITV</span>
                     <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500 inline-block"></span> Plazo Seguro</span>
                 </div>
            </div>
        </div>
    );
};
