package examenU2_020726;

import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner leer = new Scanner(System.in);

        System.out.println("=== SISTEMA DE FABRICACION DE CALZADO ===");
        System.out.println("1. Tenis tradicional");
        System.out.println("2. Zapatos");
        System.out.println("3. Botas");
        System.out.println("4. Tacon");
        System.out.println("5. Sandalias");
        System.out.print("Seleccione el tipo de calzado: ");
        int opcion = leer.nextInt();
        leer.nextLine();

        System.out.println("Seleccione la calidad del material:");
        System.out.println("1. basico");
        System.out.println("2. premium");
        System.out.print("Seleccione: ");
        int opcionCalidad = leer.nextInt();
        leer.nextLine();

        String calidad = "basico";
        double factorCalidad = 1.0;
        if (opcionCalidad == 2) {
            calidad = "premium";
            factorCalidad = 1.5;
        }

        double costoBase = 0;
        Padre_Zapato calzado = null;
        String colorDefault = "negro";

        if (opcion == 1) {
            costoBase = 500;
            calzado = new Hijo_Tenis("Tenis tradicional", colorDefault, calidad, "deportiva", "blanco", true);
        } else if (opcion == 2) {
            costoBase = 600;
            calzado = new Hijo_Zapatos("Zapatos", colorDefault, calidad, "cordones", "reforzada", true);
        } else if (opcion == 3) {
            costoBase = 800;
            calzado = new Hijo_Botas("Botas", colorDefault, calidad, 25.5, "acero", true);
        } else if (opcion == 4) {
            costoBase = 700;
            calzado = new Hijo_Tacon("Tacon", colorDefault, calidad, 10.0, "fina", true);
        } else if (opcion == 5) {
            costoBase = 400;
            calzado = new Hijo_Sandalias("Sandalias", colorDefault, calidad, 3, "hebilla", true);
        }

        if (calzado != null) {
            System.out.println("\n--- PROCESO DE FABRICACION ---");
            calzado.iniciarProceso();

            if (calzado instanceof Hijo_Tenis) {
                Hijo_Tenis t = (Hijo_Tenis) calzado;
                t.coserSuela();
                System.out.println("Retocando detalles del calzado deportivo");
                t.colocarAgujetas();
            } else if (calzado instanceof Hijo_Zapatos) {
                Hijo_Zapatos z = (Hijo_Zapatos) calzado;
                z.hormarZapato();
                System.out.println("Retocando detalles del zapato clasico");
                z.bolearZapato();
            } else if (calzado instanceof Hijo_Botas) {
                Hijo_Botas b = (Hijo_Botas) calzado;
                b.reforzarTobillo();
                System.out.println("Retocando detalles de la bota");
                b.impermeabilizar();
            } else if (calzado instanceof Hijo_Tacon) {
                Hijo_Tacon tac = (Hijo_Tacon) calzado;
                tac.fijarTacon();
                System.out.println("Retocando detalles del tacon elegante");
                tac.colocarPlantilla();
            } else if (calzado instanceof Hijo_Sandalias) {
                Hijo_Sandalias s = (Hijo_Sandalias) calzado;
                s.montarCorreas();
                System.out.println("Retocando detalles de la sandalia de verano");
                s.asegurarHebilla();
            }

            double costoTotal = costoBase * factorCalidad;
            System.out.println("Detalle finalizado exitosamente");
            System.out.println("Costo total de produccion: $" + costoTotal);
        } else {
            System.out.println("Opcion de calzado no valida");
        }

        leer.close();
    }
}
