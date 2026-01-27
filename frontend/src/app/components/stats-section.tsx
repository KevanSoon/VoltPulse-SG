"use client";

const stats = [
  {
    value: "1.13M",
    label: "HDB Units",
    description: "Public housing apartments in Singapore",
  },
  {
    value: "77%",
    label: "Population in HDB",
    description: "Residents living in public housing",
  },
  {
    value: "7.9 TWh",
    label: "Annual Consumption",
    description: "Household electricity in 2022",
  },
  {
    value: "30%",
    label: "Cooling Load",
    description: "Of total electricity for cooling",
  },
];

export function StatsSection() {
  return (
    <section className="py-16 bg-card border-y border-border">
      <div className="container mx-auto px-4 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat, index) => (
            <div key={index} className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-blue-500 mb-2">
                {stat.value}
              </div>
              <div className="text-sm font-medium text-foreground mb-1">
                {stat.label}
              </div>
              <div className="text-xs text-muted-foreground">
                {stat.description}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
