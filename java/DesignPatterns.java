package com.example;

import java.io.*;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.KeyFactory;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.text.NumberFormat;
import java.util.*;
import java.util.concurrent.*;
import java.util.logging.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * This class contains the examples of the most popular Design Patterns using the implementations
 * present in Java core packages like java.io, java.lang, java.util etc.
 *
 * <p>As the class has limited error handling, it is assumed that the pre-requisites are present.
 * Besides {@code java.sql} example in Bridge Pattern, no other method needs any third-party dependency.
 *
 * <p>The main method has the responsibility to run all the examples.
 */
public class DesignPatterns {

  // Singleton Pattern - Ensuring only one instance of Logger
  private static final Logger logger = Logger.getLogger(DesignPatterns.class.getName());

  public static void singletonPatternExample() {
    Handler consoleHandler = new ConsoleHandler();
    consoleHandler.setFormatter(
        new SimpleFormatter() {
          @Override
          public String format(LogRecord logRecord) {
            return String.format(
                "%1$tF %1$tT.%1$tL %2$s %3$s %4$s%n",
                logRecord.getMillis(),
                logRecord.getLevel().getName(),
                logRecord.getSourceClassName(),
                logRecord.getMessage());
          }
        });
    logger.addHandler(consoleHandler);
    logger.setUseParentHandlers(false);

    logger.info("Singleton Pattern Example: " + logger + " is a singleton instance");
  }

  // Factory Method Pattern - Using a KeyFactory with different providers
  public static void factoryPatternExample() throws NoSuchAlgorithmException {
    KeyFactory rsaFactory = KeyFactory.getInstance("RSA");
    logger.info("Factory Pattern Example: RSA Key provider = " + rsaFactory.getProvider());

    KeyFactory dsaFactory = KeyFactory.getInstance("DSA");
    logger.info("Factory Pattern Example: DSA Key provider = " + dsaFactory.getProvider());
  }

  // Abstract Factory Pattern - Using NumberFormat as an abstract factory
  public static void abstractFactoryPatternExample() {
    NumberFormat currencyFormat = NumberFormat.getCurrencyInstance();
    logger.info("Abstract Factory Pattern Example: Currency format = " + currencyFormat);

    NumberFormat percentFormat = NumberFormat.getPercentInstance();
    logger.info("Abstract Factory Pattern Example: Percent format = " + percentFormat);
  }

  // Builder Pattern - Using StringBuilder
  public static void builderPatternExample() {
    StringBuilder builder = new StringBuilder();
    builder.append("Hello").append(" World");
    logger.info("Builder Pattern Example: StringBuilder output = " + builder);
  }

  // Prototype Pattern - Cloning an ArrayList
  public static void prototypePatternExample() {
    List<String> originalList = new ArrayList<>(List.of("A", "B", "C"));
    logger.info("Prototype Pattern Example: Original list = " + originalList);

    List<String> clonedList = new ArrayList<>(originalList);
    logger.info("Prototype Pattern Example: Cloned List = " + clonedList);
  }

  // Adapter Pattern - Adapting the array to a List using Arrays.asList()
  public static void adapterPatternExample() {
    String[] originalArray = {"Adapter", "Pattern", "Example"};
    logger.info("Adapter Pattern Example: Original array = " + originalArray);

    List<String> adaptedList = Arrays.asList(originalArray);
    logger.info("Adapter Pattern Example: Adapted list = " + adaptedList);
  }

  // Bridge Pattern - Using the Connection abstraction with different Driver implementations
  public static void bridgePatternExample() {
    // This will log an error unless we add org.xerial:sqlite-jdbc dependency
    try (Connection connection = DriverManager.getConnection("jdbc:sqlite:/tmp/test1.db")) {
      DatabaseMetaData metaData = connection.getMetaData();
      logger.info(
          "Bridge Pattern Example: Connected to "
              + connection
              + " using "
              + metaData.getDriverName());
    } catch (SQLException e) {
      logger.severe(
          "Bridge Pattern Example: Got error while connecting to sqlite : " + e.getMessage());
    }

    // This will log an error unless we add com.h2database:h2 dependency
    try (Connection connection = DriverManager.getConnection("jdbc:h2:file:/tmp/test2.db")) {
      DatabaseMetaData metaData = connection.getMetaData();
      logger.info(
          "Bridge Pattern Example: Connected to "
              + connection
              + " using "
              + metaData.getDriverName());
    } catch (SQLException e) {
      logger.severe("Bridge Pattern Example: Got error while connecting to h2 : " + e.getMessage());
    }
  }

  // Composite Pattern - Creating a composite collection of multiple collections
  public static void compositePatternExample() {
    List<String> component1 = List.of("Item1", "Item2");
    Set<String> component2 = Set.of("Item3", "Item4", "Item5");

    List<Collection<String>> composite = new ArrayList<>();
    composite.add(component1);
    composite.add(component2);

    logger.info("Composite Pattern Example: Composite collection = " + composite);
  }

  // Decorator Pattern - Using decorators of ByteArrayInputStream
  public static void decoratorPatternExample() throws IOException {
    byte[] bytes = "Hello World!".getBytes();
    try (InputStream inputStream = new ByteArrayInputStream(bytes)) {
      InputStream bufferedInputStream = new BufferedInputStream(inputStream);
      logger.info(
          "Decorator Pattern Example: Buffered input stream = "
              + new String(bufferedInputStream.readAllBytes()));
    }

    try (InputStream inputStream = new ByteArrayInputStream(bytes)) {
      InputStream dataInputStream = new DataInputStream(inputStream);
      logger.info(
          "Decorator Pattern Example: Data input stream = "
              + new String(dataInputStream.readAllBytes()));
    }
  }

  // Facade Pattern - Using Files API which is a facade for file related operations
  public static void facadePatternExample() throws IOException {
    Path path = Files.writeString(Paths.get("/tmp/testFile"), "Hello World!");
    logger.info("Facade Pattern Example: File write path = " + path);

    String content = Files.readString(Paths.get("/tmp/testFile"));
    logger.info("Facade Pattern Example: File content = " + content);

    Files.delete(path);
    logger.info("Facade Pattern Example: Deleted file " + path);
  }

  // Flyweight Pattern - Using Integer.valueOf which caches values in the range -128 to 127
  public static void flyweightPatternExample() {
    Integer a = Integer.valueOf(100);
    Integer b = Integer.valueOf(100);
    logger.info("Flyweight Pattern Example: Using cache: " + (a == b));

    Integer c = Integer.valueOf(200);
    Integer d = Integer.valueOf(200);
    logger.info("Flyweight Pattern Example: Using cache: " + (c == d));
  }

  // Proxy Pattern - Using java.lang.reflect.Proxy to create a mocked instance of list
  public static void proxyPatternExample() {
    InvocationHandler mockedInvocationHandler =
        (proxy, method, args) -> {
          logger.info("Proxy Pattern Example: Called proxy method = " + method.getName());
          return 10;
        };

    List<?> mockedListInstance =
        (List<?>)
            Proxy.newProxyInstance(
                List.class.getClassLoader(), new Class<?>[] {List.class}, mockedInvocationHandler);

    logger.info("Proxy Pattern Example: Mocked value = " + mockedListInstance.size());
  }

  // Chain of Responsibility Pattern - Using Blocking Queues to show chain of handlers
  public static void chainOfResponsibilityExample() {
    BlockingQueue<String> queue1 = new ArrayBlockingQueue<>(5);
    BlockingQueue<String> queue2 = new ArrayBlockingQueue<>(5);

    queue1.add("Test request");
    queue1.add("STOP");

    ExecutorService executor = Executors.newFixedThreadPool(4);
    executor.submit(
        () -> {
          while (true) {
            String request;
            try {
              request = queue1.take();
              logger.info(
                  "Chain of Responsibility Pattern Example: " + request + " handled by handler1..");
              queue2.put(request);
              if ("STOP".equals(request)) {
                break;
              }
            } catch (InterruptedException e) {
              throw new RuntimeException(e);
            }
          }
        });
    executor.submit(
        () -> {
          while (true) {
            String request;
            try {
              request = queue2.take();
              logger.info(
                  "Chain of Responsibility Pattern Example: " + request + " handled by handler2..");
              if ("STOP".equals(request)) {
                break;
              }
            } catch (InterruptedException e) {
              throw new RuntimeException(e);
            }
          }
        });

    executor.shutdown();
  }

  // Command Pattern - Using Runnable to encapsulate a command
  public static void commandPatternExample() {
    Runnable runnable = () -> logger.info("Command Pattern Example: Running encapsulated command");
    ExecutorService executor = Executors.newSingleThreadExecutor();
    executor.submit(runnable);
    executor.shutdown();
  }

  // Interpreter Pattern - Using Pattern and Matcher
  public static void interpreterPatternExample() {
    Pattern pattern = Pattern.compile("\\d+");
    Matcher matcher = pattern.matcher("123ABC");
    logger.info("Interpreter Pattern Example: Regex pattern matched = " + matcher.find());
  }

  // Iterator Pattern - Creating a custom Iterator
  public static void iteratorPatternExample() {
    Iterator<Integer> itr =
        new Iterator<>() {
          int count = 0;

          @Override
          public boolean hasNext() {
            count++;
            return count < 3;
          }

          @Override
          public Integer next() {
            return count;
          }
        };

    while (itr.hasNext()) {
      logger.info("Iterator Pattern Example: Next element = " + itr.next());
    }
  }

  // Mediator Pattern - Using java.util.Timer as a mediator to schedule tasks
  public static void mediatorPatternExample() {
    Timer timer = new Timer();

    TimerTask task1 =
        new TimerTask() {
          @Override
          public void run() {
            logger.info("Mediator Pattern Example: Executing Task 1..");
          }
        };

    TimerTask task2 =
        new TimerTask() {
          @Override
          public void run() {
            logger.info("Mediator Pattern Example: Executing Task 2..");
            timer.cancel();
          }
        };

    timer.schedule(task1, 10);
    timer.schedule(task2, 20);
  }

  // Observer Pattern - Using java.util.concurrent.Flow for publishing and subscribing
  public static void observerPatternExample() {
    Flow.Subscriber<String> subscriber =
        new Flow.Subscriber<>() {
          @Override
          public void onSubscribe(Flow.Subscription subscription) {
            subscription.request(2);
          }

          @Override
          public void onNext(String item) {
            logger.info("Observed Pattern Example: Next item = " + item);
          }

          @Override
          public void onError(Throwable throwable) {
            logger.severe("Observed Pattern Example: Got error : " + throwable.getMessage());
          }

          @Override
          public void onComplete() {
            logger.info("Observed Pattern Example: No more Items..");
          }
        };

    try (SubmissionPublisher<String> publisher = new SubmissionPublisher<>()) {
      publisher.subscribe(subscriber);
      publisher.submit("Item1");
      publisher.submit("Item2");
    }
  }

  // State Pattern - Creating a child thread and checking its states
  public static void statePatternExample() {
    Thread thread = new Thread(() -> logger.info("State Pattern Example: Executing runnable.."));
    logger.info("State Pattern Example: Thread state = " + thread.getState());

    thread.start();
    logger.info("State Pattern Example: Thread state = " + thread.getState());

    try {
      thread.join();
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
    }
    logger.info("State Pattern Example: Thread state = " + thread.getState());
  }

  // Strategy Pattern - Using Comparators for a list of strings
  public static void strategyPatternExample() {
    Comparator<String> comparator1 = (s1, s2) -> s1.compareTo(s2);
    Comparator<String> comparator2 =
        (s1, s2) -> {
          int lengthComparison = Integer.compare(s1.length(), s2.length());
          return (lengthComparison != 0) ? lengthComparison : s1.compareTo(s2);
        };
    List<String> list = Arrays.asList("Alice", "Bob", "Cody");
    list.sort(comparator1);
    logger.info("Strategy Pattern Example: Lexicographically sorted list = " + list);

    list.sort(comparator2);
    logger.info("Strategy Pattern Example: Length-sorted list = " + list);
  }

  // Template Method Pattern - Using AbstractList template
  public static void templateMethodExample() {
    AbstractList<Integer> customList =
        new AbstractList<>() {
          private final Set<Integer> data = new LinkedHashSet<>();

          @Override
          public boolean add(Integer element) {
            data.add(element);
            return true;
          }

          @Override
          public Integer get(int index) {
            return data.stream().toList().get(index);
          }

          @Override
          public int size() {
            return data.size();
          }
        };

    customList.add(43);
    customList.add(43);
    customList.add(44);

    logger.info("Template Method Example: Size of custom list = " + customList.size());
  }

  public static void main(String[] args) throws Exception {

    // Creational Design Patterns
    singletonPatternExample();
    factoryPatternExample();
    abstractFactoryPatternExample();
    builderPatternExample();
    prototypePatternExample();

    // Structural Design Patterns
    adapterPatternExample();
    bridgePatternExample();
    compositePatternExample();
    decoratorPatternExample();
    facadePatternExample();
    flyweightPatternExample();
    proxyPatternExample();

    // Behavioral Design Patterns
    chainOfResponsibilityExample();
    commandPatternExample();
    interpreterPatternExample();
    iteratorPatternExample();
    mediatorPatternExample();
    observerPatternExample();
    statePatternExample();
    strategyPatternExample();
    templateMethodExample();
  }
}
