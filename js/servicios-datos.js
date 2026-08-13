/* Datos de servicios y subservicios con fotos (servicios.html) */
var SERVICIOS_DATOS = [
  {
    key: "consultorias",
    num: "01",
    nombre: "Consultorías",
    desc: "Diseño arquitectónico, estructural, hidráulico y de vías para proyectos residenciales, comerciales e institucionales, con estudios de viabilidad y acompañamiento técnico en cada etapa.",
    foto: "img/consultoria-despues.jpg",
    subservicios: [
      { nombre: "Diseño arquitectónico y estructural", desc: "Planos y diseño estructural a la medida del proyecto, cumpliendo la normatividad vigente.", foto: "img/consultoria-despues.jpg" },
      { nombre: "Diseño hidráulico y de vías", desc: "Diseño de redes hidráulicas y vías con criterios técnicos y estudios previos.", foto: "img/consultoria-antes.png" },
      { nombre: "Proyectos residenciales, comerciales e institucionales", desc: "Desarrollo de proyectos en diferentes escalas y sectores.", foto: "img/consultoria-despues.jpg" },
      { nombre: "Estudios de viabilidad y asesoría técnica", desc: "Evaluación técnica y económica del proyecto antes de ejecutar.", foto: "img/consultoria-antes.png" }
    ]
  },
  {
    key: "estructuras",
    num: "02",
    nombre: "Estructuras Metálicas",
    desc: "Construcción de estructuras metálicas para edificaciones, bodegas, cubiertas y carpintería metálica, con fabricación y montaje certificado.",
    foto: "img/estructuras-despues.png",
    subservicios: [
      { nombre: "Edificaciones, bodegas y cubiertas", desc: "Estructuras metálicas para naves, bodegas y edificaciones industriales.", foto: "img/estructuras-despues.png" },
      { nombre: "Carpintería metálica", desc: "Puertas, ventanas, rejas, pasamanos y trabajos a la medida.", foto: "img/estructuras-antes.png" },
      { nombre: "Fabricación y montaje certificado", desc: "Fabricación y montaje con personal calificado y certificaciones.", foto: "img/estructuras-despues.png" },
      { nombre: "Soldadura y trabajos en acero", desc: "Soldadura especializada y trabajos en acero estructural.", foto: "img/estructuras-antes.png" }
    ]
  },
  {
    key: "redes-urbanismo",
    num: "03",
    nombre: "Redes de Urbanismo",
    desc: "Construcción de redes de alcantarillado e hidráulicas, registros de inspección (manjoles) y estructuras para el manejo de aguas lluvias.",
    foto: "img/redes-urbanismo.png",
    subservicios: [
      { nombre: "Redes de alcantarillado sanitario", desc: "Instalación de redes sanitarias para urbanizaciones y proyectos.", foto: "img/redes-urbanismo-2.png" },
      { nombre: "Registros de inspección (manjoles)", desc: "Construcción de manjoles y registros de inspección de redes.", foto: "img/redes-urbanismo-3.png" },
      { nombre: "Estructuras para manejo de aguas lluvias", desc: "Sistemas de captación y conducción de aguas lluvias.", foto: "img/redes-urbanismo.png" },
      { nombre: "Obra urbana e infraestructura", desc: "Urbanismo general y obra civil de infraestructura.", foto: "img/redes-urbanismo-2.png" }
    ]
  },
  {
    key: "hidraulicas",
    num: "04",
    nombre: "Instalaciones Hidráulicas y Sanitarias",
    desc: "Instalación de redes hidráulicas y sanitarias, con suministro de macromedidores y micromedidores y cumplimiento de la normatividad vigente.",
    foto: "img/hidraulicas-sanitarias.png",
    subservicios: [
      { nombre: "Redes hidráulicas y sanitarias", desc: "Instalación de redes de agua potable y sanitarias.", foto: "img/hidraulicas-sanitarias.png" },
      { nombre: "Suministro de macromedidores y micromedidores", desc: "Medidores de agua para proyectos y edificaciones.", foto: "img/chatgpt-hidraulicas.png" },
      { nombre: "Diseño e instalación de redes domiciliarias", desc: "Redes internas y acometidas domiciliarias.", foto: "img/hidraulicas-sanitarias.png" },
      { nombre: "Cumplimiento de normatividad vigente", desc: "Trabajos conforme a la reglamentación técnica colombiana.", foto: "img/chatgpt-hidraulicas.png" }
    ]
  },
  {
    key: "incendios",
    num: "05",
    nombre: "Redes Contra Incendios",
    desc: "Diseño e instalación de sistemas contra incendios para proteger vidas y bienes: redes de hidrantes, gabinetes, rociadores y estaciones de bombeo, cumpliendo la normatividad vigente.",
    foto: "img/redes-incendios.png",
    subservicios: [
      { nombre: "Redes de hidrantes y gabinetes", desc: "Instalación de hidrantes y gabinetes contra incendios.", foto: "img/redes-incendios.png" },
      { nombre: "Sistemas de rociadores automáticos", desc: "Diseño e instalación de rociadores automáticos.", foto: "img/chatgpt-incendios.png" },
      { nombre: "Estaciones de bombeo y tanques", desc: "Bombas y tanques de reserva para sistemas de protección.", foto: "img/redes-incendios.png" },
      { nombre: "Cumplimiento de la normatividad vigente", desc: "Sistemas conforme a la NSR y normatividad técnica.", foto: "img/chatgpt-incendios.png" }
    ]
  },
  {
    key: "vias",
    num: "06",
    nombre: "Construcción de Vías",
    desc: "Pavimento rígido y pavimento articulado (adoquín) para vías urbanas, accesos y zonas de tránsito vehicular, con preparación de subbase y nivelación.",
    foto: "img/vias-despues.png",
    subservicios: [
      { nombre: "Pavimento rígido en concreto", desc: "Construcción de vías y losas en concreto rígido.", foto: "img/vias-despues.png" },
      { nombre: "Pavimento articulado (adoquín)", desc: "Vías y zonas peatonales en adoquín.", foto: "img/vias-antes.png" },
      { nombre: "Vías urbanas, accesos y parqueaderos", desc: "Obras viales urbanas, accesos y parqueaderos.", foto: "img/vias-despues.png" },
      { nombre: "Preparación de subbase y nivelación", desc: "Preparación de subbase granular y nivelación de terrenos.", foto: "img/vias-antes.png" }
    ]
  },
  {
    key: "impermeabilizacion",
    num: "07",
    nombre: "Impermeabilización",
    desc: "Impermeabilización de cubiertas y zonas comunes para proteger las edificaciones de filtraciones y humedad, con tratamiento y sellado de superficies.",
    foto: "img/impermeabilizacion.png",
    subservicios: [
      { nombre: "Cubiertas y terrazas", desc: "Impermeabilización de cubiertas y terrazas.", foto: "img/impermeabilizacion.png" },
      { nombre: "Zonas comunes y fachadas", desc: "Protección de zonas comunes y fachadas.", foto: "img/impermeabilizacion.png" },
      { nombre: "Protección contra filtraciones", desc: "Soluciones para evitar filtraciones y humedad.", foto: "img/impermeabilizacion.png" },
      { nombre: "Tratamiento de humedad y sellado", desc: "Tratamiento de humedad y sellado de superficies.", foto: "img/impermeabilizacion.png" }
    ]
  },
  {
    key: "acabados",
    num: "08",
    nombre: "Acabados y Mampostería",
    desc: "Levante de muros, pañete, estuco, pintura, acabados y mantenimiento de fachadas de edificios, además de remodelaciones y adecuaciones.",
    foto: "img/blanco-fondo.jpg",
    subservicios: [
      { nombre: "Levante de muros y pañete", desc: "Mampostería y pañetes en obra.", foto: "img/blanco-fondo.jpg" },
      { nombre: "Estuco, pintura y acabados", desc: "Estuco, pintura y acabados finos.", foto: "img/blanco-fondo.jpg" },
      { nombre: "Mantenimiento de fachadas", desc: "Mantenimiento y restauración de fachadas.", foto: "img/blanco-fondo.jpg" },
      { nombre: "Remodelaciones y adecuaciones", desc: "Remodelaciones y adecuaciones de espacios.", foto: "img/blanco-fondo.jpg" }
    ]
  },
  {
    key: "mantenimiento-ac",
    num: "09",
    nombre: "Mantenimiento A/C",
    desc: "Servicio especializado de mantenimiento correctivo y preventivo de aires acondicionados, residenciales, comerciales e industriales, con atención 24/7.",
    foto: "img/mantenimiento-ac.png",
    subservicios: [
      { nombre: "Mantenimiento preventivo programado", desc: "Planes de mantenimiento preventivo programado.", foto: "img/mantenimiento-ac.png" },
      { nombre: "Mantenimiento correctivo y diagnóstico", desc: "Diagnóstico y reparación de equipos de A/C.", foto: "img/mantenimiento-ac.png" },
      { nombre: "Equipos residenciales, comerciales e industriales", desc: "Mantenimiento de A/C en todo tipo de equipos.", foto: "img/mantenimiento-ac.png" },
      { nombre: "Atención de urgencias 24/7", desc: "Soporte y atención de urgencias las 24 horas.", foto: "img/mantenimiento-ac.png" }
    ]
  }
];
